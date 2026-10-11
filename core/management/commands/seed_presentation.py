"""Datos ficticios de presentación: repetibles, sin modificar registros existentes."""
from datetime import date

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from activities.models import Activity, ServiceCatalog, Vecino
from metrics.models import AttentionType, Goal, MeasurementItem, MeasurementPeriod, SubAttention, ManagementType
from organization.models import Delegation, Position, Role, UserProfile


def example_rut(number):
    digits = str(number)
    remainder = 11 - sum(int(d) * (2 + i % 6) for i, d in enumerate(reversed(digits))) % 11
    return f'{digits}-{ {11: "0", 10: "K"}.get(remainder, str(remainder))}'


class Command(BaseCommand):
    help = 'Agrega tres ejemplos por catálogo sin alterar cuentas, cargos ni permisos existentes.'

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError('Esta carga ficticia está habilitada solo en desarrollo (DEBUG).')
        position = Position.objects.filter(name='Gestor Territorial', deleted_at=None, status='Activo').first()
        role = Role.objects.filter(name='Gestor Territorial', deleted_at=None).first()
        names = ['Delegación Centro Histórico', 'Delegación Las Compañías', 'Delegación La Pampa']
        delegations = [Delegation.objects.filter(name=name, deleted_at=None, status='Activo').first() for name in names]
        if not position or not role or not all(delegations):
            raise CommandError('Faltan el cargo, rol o delegaciones base. No se modificó ningún dato.')
        today = timezone.localdate()
        period, _ = MeasurementPeriod.objects.get_or_create(
            name='Período de ejemplo', defaults={
                'start_date': date(today.year, 1, 1), 'end_date': date(today.year, 12, 31),
                'computable_days': 240,
            })
        samples = [
            ('Camila', 'Rojas', 'Orientación social', 'Información de beneficios', 40, 20),
            ('Tomás', 'Vega', 'Atención territorial', 'Consulta de espacios públicos', 35, 15),
            ('Valentina', 'Soto', 'Apoyo comunitario', 'Orientación a organizaciones', 25, 10),
        ]
        for index, (first, last, service_name, subtype, weight, target) in enumerate(samples, 1):
            email = f'ejemplo.sgr.{index}@example.invalid'
            user, created = get_user_model().objects.get_or_create(
                username=f'ejemplo_sgr_{index}', defaults={
                    'first_name': first, 'last_name': f'{last} Ejemplo', 'email': email,
                    'is_active': False,
                })
            if created:
                user.set_unusable_password()
                user.save(update_fields=['password'])
            elif user.email != email or user.is_staff or user.is_superuser:
                raise CommandError('Un identificador de ejemplo ya pertenece a otra cuenta. Carga cancelada.')
            delegation = delegations[index - 1]
            profile, created = UserProfile.objects.get_or_create(user=user, defaults={
                'rut': example_rut(99000100 + index), 'full_name': f'{first} {last} Ejemplo',
                'email': email, 'delegation': delegation, 'position': position, 'status': 'Inactivo',
            })
            if created:
                profile.roles.add(role)
            attention, _ = AttentionType.objects.get_or_create(code=f'EJ-T{index}', defaults={
                'name': f'{service_name} (ejemplo)', 'description': 'Dato ficticio para presentación académica.',
            })
            sub, _ = SubAttention.objects.get_or_create(code=f'EJ-S{index}', defaults={
                'name': f'{subtype} (ejemplo)', 'attention_type': attention,
            })
            item, _ = MeasurementItem.objects.get_or_create(code=f'EJ-I{index}', defaults={
                'name': f'{service_name} (ejemplo)', 'description': 'Conteo de atenciones de ejemplo.',
            })
            Goal.objects.get_or_create(code=f'EJ-M{index}', defaults={
                'period': period, 'position': position, 'item': item, 'target_value': target, 'weight': weight,
            })
            catalog, _ = ServiceCatalog.objects.get_or_create(
                area='Presentación académica', service=f'{service_name} (ejemplo)',
                defaults={'attention_type': attention.name, 'subattention_type': sub.name})
            vecino, _ = Vecino.objects.get_or_create(rut=example_rut(99000200 + index), defaults={
                'nombre': f'Vecino Ficticio {index}', 'direccion': f'Dirección de ejemplo {index}',
                'territorio': delegation.name,
            })
            Activity.objects.get_or_create(activity_code=f'EJ-AT-{index:03}', defaults={
                'user': user, 'delegation': delegation, 'period': period, 'item': item,
                'catalog': catalog, 'attention_type': attention, 'subattention': sub,
                'activity_date': today, 'contact_name': vecino.nombre,
                'problem_description': f'Ejemplo ficticio: consulta sobre {service_name.lower()}.',
                'executed_action': 'Se entrega orientación inicial. Registro académico sin atención real.',
            })
        for index, name in enumerate(['Ingreso de antecedentes', 'Evaluación y derivación', 'Resolución y cierre'], 1):
            ManagementType.objects.get_or_create(code=f'EJ-G{index}', defaults={
                'name': f'{name} (ejemplo)', 'description': f'Etapa {index} del flujo de ejemplo. Catálogo editable; no automatiza transiciones de casos.',
            })
        self.stdout.write(self.style.SUCCESS(
            'Ejemplos disponibles: 3 perfiles inactivos, vecinos, tipos, subatenciones, ítems, metas, servicios y atenciones. Sin duplicados ni claves de acceso.'
        ))
