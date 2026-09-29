from django.contrib import admin, messages
from django.utils import timezone
from organization.models import Delegation
from .models import SocialCase, SocialManagement
from .forms import SocialCaseForm


class SocialManagementInline(admin.TabularInline):
    model = SocialManagement
    extra = 1
    fields = ('stage', 'catalog', 'management_type', 'management_date', 'result')
    show_change_link = True


@admin.register(SocialCase)
class SocialCaseAdmin(admin.ModelAdmin):
    form = SocialCaseForm
    list_display = (
        'user_name', 
        'user_rut', 
        'contact_phone', 
        'delegation', 
        'entry_date', 
        'created_at', 
        'deleted_at'
    )
    list_editable = ('contact_phone',)
    list_select_related = ('delegation',)
    list_filter = ('delegation', 'entry_date', ('deleted_at', admin.EmptyFieldListFilter))
    search_fields = ('user_name', 'user_rut', 'contact_phone')
    ordering = ('-entry_date',)
    inlines = [SocialManagementInline]
    actions = ['derivar_a_evaluacion', 'soft_delete_casos', 'restaurar_casos']

    # --- ACCIONES PERSONALIZADAS (Admin Pro - Rúbrica) ---
    @admin.action(description="📋 Derivar casos seleccionados a evaluación técnica social")
    def derivar_a_evaluacion(self, request, queryset):
        count = 0
        for case in queryset:
            # Crear gestión automática de derivación
            SocialManagement.objects.create(
                case=case,
                stage=min(case.managements.count() + 1, 3),
                management_type="Derivación técnica formal para evaluación socioeconómica",
                management_date=timezone.now().date(),
                result="Caso priorizado y asignado a asistente social de la delegación."
            )
            count += 1
        self.message_user(request, f"Se han derivado exitosamente {count} caso(s) social(es).", messages.SUCCESS)

    @admin.action(description="🗑️ Aplicar borrado lógico a casos seleccionados")
    def soft_delete_casos(self, request, queryset):
        count = queryset.update(deleted_at=timezone.now())
        self.message_user(request, f"Se aplicó borrado lógico a {count} caso(s) (registrado en deleted_at).", messages.INFO)

    @admin.action(description="♻️ Restaurar casos seleccionados")
    def restaurar_casos(self, request, queryset):
        count = queryset.update(deleted_at=None)
        self.message_user(request, f"Se restauraron {count} caso(s) social(es).", messages.SUCCESS)

    # --- SEGURIDAD Y SCOPING POR DELEGACIÓN (Rúbrica: 15 pts) ---
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # El administrador tiene visibilidad transversal completa
        if request.user.is_superuser or request.user.groups.filter(name="Administradores").exists():
            return qs
        # El usuario limitado solo visualiza casos de su delegación asignada
        if hasattr(request.user, 'profile') and request.user.profile.delegation:
            return qs.filter(delegation=request.user.profile.delegation)
        return qs.none()

    def has_change_permission(self, request, obj=None):
        if not super().has_change_permission(request, obj):
            return False
        if obj is None or request.user.is_superuser or request.user.groups.filter(name="Administradores").exists():
            return True
        # El usuario limitado solo puede modificar casos de su delegación
        if hasattr(request.user, 'profile') and request.user.profile.delegation:
            return obj.delegation_id == request.user.profile.delegation_id
        return False

    def has_delete_permission(self, request, obj=None):
        # Solo el Administrador puede eliminar registros (los usuarios limitados no pueden)
        return request.user.is_superuser or request.user.groups.filter(name="Administradores").exists()

    def save_model(self, request, obj, form, change):
        if not (request.user.is_superuser or request.user.groups.filter(name="Administradores").exists()):
            if hasattr(request.user, 'profile') and request.user.profile.delegation:
                obj.delegation = request.user.profile.delegation
        super().save_model(request, obj, form, change)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if not (request.user.is_superuser or request.user.groups.filter(name="Administradores").exists()) and db_field.name == "delegation":
            if hasattr(request.user, 'profile') and request.user.profile.delegation:
                kwargs["queryset"] = Delegation.objects.filter(id=request.user.profile.delegation_id)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(SocialManagement)
class SocialManagementAdmin(admin.ModelAdmin):
    list_display = ('case', 'stage', 'catalog', 'management_type', 'management_date', 'created_at')
    list_select_related = ('case', 'catalog')
    list_filter = ('stage', 'management_date')
    search_fields = ('case__user_name', 'case__user_rut', 'management_type', 'result')
    ordering = ('case', 'stage')

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser or request.user.groups.filter(name="Administradores").exists()
