"""Una cuenta y doce atenciones ficticias para presentar el CRUD del delegado."""
import os

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone

from activities.models import Activity, Vecino
from activities.views import _normalize_vecino_rut, _valid_vecino_rut
from core.management.commands.seed_presentation import example_rut
from metrics.models import AttentionType, SubAttention
from organization.models import Delegation, Position, Role, UserProfile


USERNAME = 'delegado.demo'
EMAIL = 'delegado.demo@example.test'
PROFILE_NAME = 'Delegado de demostración SGR'
PROFILE_RUT = example_rut(99001000)
CODE_PREFIX = 'DEMO-DEL-'
RECORD_COUNT = 12


class Command(BaseCommand):
    help = 'Prepara un delegado y 12 atenciones ficticias en desarrollo, sin reemplazar datos existentes.'

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError('Esta carga ficticia está habilitada solo en desarrollo (DEBUG).')
        try:
            with transaction.atomic():
                profile, created_count = self.seed()
        except (ValidationError, IntegrityError) as exc:
            raise CommandError('Los datos de demostración no son válidos o colisionan con datos existentes. No se guardó ningún cambio.') from exc
        live = Activity.objects.filter(
            user=profile.user, activity_code__startswith=CODE_PREFIX, deleted_at__isnull=True,
        ).count()
        self.stdout.write(self.style.SUCCESS(
            f'Delegado disponible: {USERNAME} ({EMAIL}), {profile.delegation.name}. '
            f'Atenciones nuevas: {created_count}; de demostración vigentes: {live}. '
            'Busca DEMO-DEL y filtra Pendiente para demostrar la paginación. '
            'Se conservaron las contraseñas, ediciones y bajas existentes.'
        ))

    def seed(self):
        position = Position.objects.filter(name='Delegado Municipal', status='Activo', deleted_at__isnull=True).first()
        role = Role.objects.filter(name='Delegado Municipal', deleted_at__isnull=True).first()
        if not position or not role:
            raise CommandError('Faltan el cargo o rol Delegado Municipal. Ejecuta las migraciones y seed_data primero.')
        profile = self.account(position, role)
        subattention = self.attention_catalog()
        created_count = 0
        for index in range(1, RECORD_COUNT + 1):
            code = f'{CODE_PREFIX}{index:03d}'
            existing = Activity.objects.filter(activity_code=code).first()
            # A deleted or edited example stays that way when this command is repeated.
            if existing:
                if (existing.user_id != profile.user_id
                        or existing.delegation_id != profile.delegation_id
                        or getattr(existing, 'social_case', None)):
                    raise CommandError(f'El código {code} ya pertenece a otro registro. Carga cancelada.')
                continue
            neighbor = self.neighbor(index, profile.delegation)
            if neighbor.deleted_at or neighbor.estado != 'Activo':
                raise CommandError('Un vecino de demostración fue dado de baja. No se restaurará ni se crearán atenciones con él.')
            activity = Activity(
                activity_code=code, user=profile.user, delegation=profile.delegation,
                neighbor=neighbor, attention_type=subattention.attention_type, subattention=subattention,
                activity_date=timezone.localdate(), contact_name=neighbor.nombre,
                contact_phone=neighbor.telefono or '',
                problem_description=f'Demostración ficticia {index:02d}: consulta de alumbrado vecinal.',
                executed_action='Se registra la consulta de prueba y se entrega orientación. Sin atención ciudadana real.',
                validation_status='Pending',
            )
            activity.full_clean()
            activity.save()
            created_count += 1
        return profile, created_count

    def account(self, position, role):
        User = get_user_model()
        user = User.objects.filter(username__iexact=USERNAME).first()
        if user:
            profile = UserProfile.objects.filter(user=user).select_related('delegation').first()
            if (user.username != USERNAME or user.email != EMAIL or user.is_staff or user.is_superuser
                    or not user.is_active or not user.has_usable_password() or not profile or profile.email != EMAIL
                    or _normalize_vecino_rut(profile.rut) != _normalize_vecino_rut(PROFILE_RUT)
                    or profile.full_name != PROFILE_NAME or profile.position_id != position.pk
                    or profile.deleted_at or profile.status != 'Activo'
                    or not profile.delegation or profile.delegation.deleted_at
                    or profile.delegation.status != 'Activo'
                    or not profile.roles.filter(pk=role.pk).exists()):
                raise CommandError('La cuenta delegado.demo ya existe con datos distintos. No se modificó su perfil ni contraseña.')
            return profile
        if User.objects.filter(email__iexact=EMAIL).exists() or UserProfile.objects.filter(email__iexact=EMAIL).exists():
            raise CommandError('El correo reservado de demostración ya está en uso. No se modificó ninguna cuenta.')
        if any(_normalize_vecino_rut(rut) == _normalize_vecino_rut(PROFILE_RUT)
               for rut in UserProfile.objects.values_list('rut', flat=True)):
            raise CommandError('El RUT ficticio del delegado ya está en uso. No se modificó ninguna cuenta.')
        delegation = Delegation.objects.filter(status='Activo', deleted_at__isnull=True)
        delegation = delegation.filter(name='Delegación Las Compañías').first() or delegation.order_by('name', 'pk').first()
        if not delegation:
            raise CommandError('No hay una delegación activa. Ejecuta las migraciones y seed_data primero.')
        password = os.environ.get('SGR_DELEGADO_DEMO_PASSWORD', '')
        if not password:
            raise CommandError('Define SGR_DELEGADO_DEMO_PASSWORD para crear la cuenta local por primera vez.')
        user = User(username=USERNAME, email=EMAIL, first_name='Delegado', last_name='Demostración SGR')
        validate_password(password, user=user)
        user.set_password(password)
        user.full_clean()
        user.save()
        if not _valid_vecino_rut(PROFILE_RUT):
            raise CommandError('El RUT ficticio de demostración no es válido.')
        profile = UserProfile(
            user=user, rut=PROFILE_RUT, full_name=PROFILE_NAME, email=EMAIL,
            position=position, delegation=delegation, status='Activo',
        )
        profile.full_clean()
        profile.save()
        profile.roles.add(role)
        return profile

    def attention_catalog(self):
        existing = SubAttention.objects.filter(
            status='Activo', deleted_at__isnull=True,
            attention_type__status='Activo', attention_type__deleted_at__isnull=True,
        ).select_related('attention_type').order_by('pk').first()
        if existing:
            return existing
        # A fresh local database may not contain any typed catalog yet.
        attention, created = AttentionType.objects.get_or_create(code='DEMO-DEL-T', defaults={
            'name': 'Orientación vecinal (demostración)', 'description': 'Catálogo ficticio para la presentación local.',
        })
        if (attention.deleted_at or attention.status != 'Activo'
                or attention.name != 'Orientación vecinal (demostración)'):
            raise CommandError('El tipo de demostración ya existe con datos distintos. No se reemplazará.')
        subattention, created = SubAttention.objects.get_or_create(code='DEMO-DEL-S', defaults={
            'name': 'Consulta de alumbrado (demostración)', 'attention_type': attention,
        })
        if (subattention.deleted_at or subattention.status != 'Activo'
                or subattention.attention_type_id != attention.pk
                or subattention.name != 'Consulta de alumbrado (demostración)'):
            raise CommandError('La subatención de demostración ya existe con datos distintos. No se reemplazará.')
        return subattention

    def neighbor(self, index, delegation):
        rut = example_rut(99001100 + index)
        email = f'vecino.delegado.demo.{index:02d}@example.test'
        matches = [neighbor for neighbor in Vecino.objects.filter(Q(email__iexact=email) | Q(rut=rut))]
        normalized_matches = [neighbor for neighbor in Vecino.objects.exclude(pk__in=[item.pk for item in matches])
                              if _normalize_vecino_rut(neighbor.rut) == _normalize_vecino_rut(rut)]
        matches += normalized_matches
        if matches:
            if (len(matches) != 1 or _normalize_vecino_rut(matches[0].rut) != _normalize_vecino_rut(rut)
                    or matches[0].email != email or matches[0].territorio != delegation.name):
                raise CommandError(f'El vecino ficticio {index:02d} colisiona con un registro existente. Carga cancelada.')
            return matches[0]
        if not _valid_vecino_rut(rut):
            raise CommandError('El RUT ficticio de un vecino no es válido.')
        neighbor = Vecino(
            nombre=f'Vecino ficticio demostración {index:02d}', rut=rut, email=email,
            direccion=f'Dirección ficticia de demostración {index:02d}', territorio=delegation.name,
            estado='Activo',
        )
        neighbor.full_clean()
        neighbor.save()
        return neighbor
