"""Administrative JSON endpoints for evaluation catalogs."""
import json
import math
from django import forms
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from organization.models import UserProfile
from .models import AttentionType, Goal, MeasurementItem, SubAttention, ManagementType
from .validation import catalog_id


class CatalogForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field, forms.ModelChoiceField):
                field.queryset = field.queryset.filter(deleted_at__isnull=True)
        self._invalid_types = []
        self.data = self.data.copy()
        # ModelForm otherwise coerces booleans, arrays and objects to strings/IDs.
        for name, field in self.fields.items():
            if name not in self.data:
                continue
            value = self.data[name]
            valid = True
            if isinstance(field, forms.ModelChoiceField):
                try:
                    catalog_id(value)
                except ValueError:
                    valid = False
            elif isinstance(field, forms.DecimalField):
                valid = (not isinstance(value, bool) and isinstance(value, (str, int, float))
                         and (not isinstance(value, float) or math.isfinite(value)))
            else:
                valid = isinstance(value, str)
            if not valid:
                self._invalid_types.append(name)
                # Reject before Django field conversion (e.g. int(Infinity)).
                self.data[name] = None

    def clean(self):
        data = super().clean()
        for name in self._invalid_types:
            self.add_error(name, 'Tipo de dato inválido.')
        return data


class ItemForm(CatalogForm):
    class Meta:
        model = MeasurementItem
        fields = ('code', 'name', 'description', 'item_type', 'status')


class GoalForm(CatalogForm):
    class Meta:
        model = Goal
        fields = ('code', 'period', 'position', 'item', 'target_value', 'unit_of_measure', 'weight', 'status')


class TypeForm(CatalogForm):
    class Meta:
        model = AttentionType
        fields = ('code', 'name', 'description', 'status')


class SubForm(CatalogForm):
    class Meta:
        model = SubAttention
        fields = ('code', 'name', 'attention_type', 'description', 'status')


class ManagementTypeForm(CatalogForm):
    class Meta:
        model = ManagementType
        fields = ('code', 'name', 'description', 'status')


CATALOGS = {'items': (MeasurementItem, ItemForm), 'goals': (Goal, GoalForm),
            'attention-types': (AttentionType, TypeForm), 'subattentions': (SubAttention, SubForm),
            'management-types': (ManagementType, ManagementTypeForm)}


def serialize(obj):
    data = {'id': obj.pk}
    for field in obj._meta.concrete_fields:
        if field.name in ('id', 'created_at', 'updated_at', 'deleted_at'):
            continue
        value = getattr(obj, field.attname)
        data[field.name] = str(value) if field.get_internal_type() == 'DecimalField' else value
    return data


def error(message, status=400, details=None):
    payload = {'error': message}
    if details is not None:
        payload['details'] = details
    return JsonResponse(payload, status=status)


def authorized(request):
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated or not user.is_active:
        return False
    return user.is_superuser or UserProfile.objects.filter(
        user=user, status='Activo', deleted_at__isnull=True,
        roles__name='Administrador General', roles__deleted_at__isnull=True,
    ).exists()


def body(request):
    try:
        value = json.loads(request.body)
    except (ValueError, UnicodeDecodeError):
        raise ValueError('JSON inválido.')
    if not isinstance(value, dict):
        raise ValueError('Se requiere un objeto JSON.')
    return value


def validate_extra(model, data, instance=None):
    code = (data.get('code') or '').strip()
    if not code:
        return {'code': ['El código es obligatorio.']}
    duplicate_code = model.objects.filter(code__iexact=code)
    if instance:
        duplicate_code = duplicate_code.exclude(pk=instance.pk)
    if duplicate_code.exists():
        return {'code': ['El código ya existe.']}
    if model in (MeasurementItem, AttentionType, ManagementType) and data.get('name'):
        duplicate_name = model.objects.filter(name__iexact=data['name'])
        if instance:
            duplicate_name = duplicate_name.exclude(pk=instance.pk)
        if duplicate_name.exists():
            return {'name': ['El nombre ya existe.']}
    if model is Goal and all(data.get(key) for key in ('period', 'position', 'item')):
        qs = Goal.objects.filter(period=data['period'], position=data['position'], item=data['item'])
        if instance:
            qs = qs.exclude(pk=instance.pk)
        if qs.exists():
            return {'__all__': ['Ya existe esta meta para el período, cargo e ítem.']}
    if model is SubAttention and data.get('attention_type') and data.get('name'):
        qs = SubAttention.objects.filter(attention_type=data['attention_type'], name__iexact=data['name'])
        if instance:
            qs = qs.exclude(pk=instance.pk)
        if qs.exists():
            return {'name': ['Ya existe esta subatención para el tipo.']}
    return None


def save_form(model, form, instance=None):
    if not form.is_valid():
        return error('Datos inválidos.', details=form.errors.get_json_data())
    extra = validate_extra(model, form.cleaned_data, instance)
    if extra:
        return error('Datos duplicados.', details=extra)
    try:
        with transaction.atomic():
            obj = form.save(commit=False)
            obj.full_clean()
            obj.save()
    except (IntegrityError, ValidationError) as exc:
        return error('Datos inválidos o duplicados.', details=str(exc))
    return JsonResponse(serialize(obj), status=201 if instance is None else 200)


def defaults(model, data):
    data = dict(data)
    data.setdefault('status', 'Activo')
    if model in (MeasurementItem, AttentionType, SubAttention, ManagementType):
        data.setdefault('description', '')
    if model is MeasurementItem:
        data.setdefault('item_type', 'Cuantitativo')
    if model is Goal:
        data.setdefault('unit_of_measure', 'Atenciones')
    return data


@require_http_methods(['GET', 'POST'])
def catalog_collection(request, catalog):
    if not authorized(request):
        return error('Se requiere una cuenta administradora.', 403)
    if catalog not in CATALOGS:
        return error('Catálogo desconocido.', 404)
    model, form_class = CATALOGS[catalog]
    if request.method == 'POST':
        try:
            return save_form(model, form_class(defaults(model, body(request))))
        except ValueError as exc:
            return error(str(exc))
    try:
        page = int(request.GET.get('page', 1))
        size = int(request.GET.get('page_size', 20))
        if page < 1 or size < 1 or size > 100:
            raise ValueError('page debe ser positivo y page_size debe estar entre 1 y 100.')
        qs = model.objects.filter(deleted_at__isnull=True)
        search = request.GET.get('search', '').strip()[:150]
        if search:
            if model is Goal:
                qs = qs.filter(
                    Q(code__icontains=search) | Q(period__name__icontains=search)
                    | Q(position__name__icontains=search) | Q(item__name__icontains=search)
                    | Q(unit_of_measure__icontains=search)
                )
            elif model is SubAttention:
                qs = qs.filter(
                    Q(code__icontains=search) | Q(name__icontains=search)
                    | Q(description__icontains=search) | Q(attention_type__name__icontains=search)
                    | Q(attention_type__description__icontains=search)
                )
            elif model is MeasurementItem:
                qs = qs.filter(
                    Q(code__icontains=search) | Q(name__icontains=search)
                    | Q(description__icontains=search) | Q(status__icontains=search)
                    | Q(item_type__icontains=search)
                )
            else:
                qs = qs.filter(
                    Q(code__icontains=search) | Q(name__icontains=search)
                    | Q(description__icontains=search) | Q(status__icontains=search)
                )
            qs = qs.distinct()
        status_filter = request.GET.get('status')
        if status_filter:
            if status_filter not in dict(MeasurementItem.STATUS_CHOICES):
                raise ValueError('Estado inválido.')
            qs = qs.filter(status=status_filter)
        keys = ('period', 'position', 'item') if model is Goal else ('attention_type',) if model is SubAttention else ()
        for key in keys:
            value = request.GET.get(key)
            if value:
                qs = qs.filter(**{key + '_id': catalog_id(value)})
        paginator = Paginator(qs.order_by('id'), size)
        result_page = paginator.get_page(page)
        return JsonResponse({'count': paginator.count, 'page': result_page.number, 'page_size': size,
                             'results': [serialize(obj) for obj in result_page]})
    except ValueError as exc:
        return error(str(exc))


@require_http_methods(['GET', 'PATCH', 'PUT', 'DELETE'])
def catalog_detail(request, catalog, pk):
    if not authorized(request):
        return error('Se requiere una cuenta administradora.', 403)
    if catalog not in CATALOGS:
        return error('Catálogo desconocido.', 404)
    model, form_class = CATALOGS[catalog]
    obj = model.objects.filter(pk=pk, deleted_at__isnull=True).first()
    if obj is None:
        return error('Registro no encontrado.', 404)
    if request.method == 'GET':
        return JsonResponse(serialize(obj))
    if request.method == 'DELETE':
        if model is AttentionType and obj.subattentions.exists():
            return error('El tipo tiene subatenciones relacionadas.', 409)
        if model is MeasurementItem and (obj.goals.exists() or obj.activities.exists()):
            return error('El ítem tiene metas o actividades relacionadas.', 409)
        # PROTECT relationships (including historical activities) return a conflict,
        # and the transaction also catches database-enforced concurrent references.
        try:
            with transaction.atomic():
                obj.delete()
        except IntegrityError:
            return error('El registro tiene relaciones que impiden su eliminación.', 409)
        from django.http import HttpResponse
        return HttpResponse(status=204)
    try:
        data = body(request)
    except ValueError as exc:
        return error(str(exc))
    if request.method == 'PATCH':
        data = {**serialize(obj), **data}
    return save_form(model, form_class(defaults(model, data), instance=obj), obj)
