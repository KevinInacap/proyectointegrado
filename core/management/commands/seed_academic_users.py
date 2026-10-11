"""Cuentas de muestra para la evaluación local; nunca crea credenciales de acceso."""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from core.management.commands.seed_presentation import example_rut
from organization.models import Delegation, Position, Role, UserProfile


# Cada bloque contiene cinco identidades sintéticas para una sede real del catálogo.
SAMPLES = {
    'DEL-001': [('Diego', 'Felipe'), ('Emilia', 'Rivas'), ('Mateo', 'Salinas'), ('Florencia', 'Vidal'), ('Benjamín', 'Prado')],
    'DEL-002': [('Sofía', 'Araya'), ('Nicolás', 'Contreras'), ('Catalina', 'Leiva'), ('Tomás', 'Olivares'), ('Isidora', 'Pizarro')],
    'DEL-003': [('Martina', 'Fuentes'), ('Vicente', 'Morales'), ('Antonia', 'Herrera'), ('Joaquín', 'Valdés'), ('Amanda', 'Cortés')],
    'DEL-004': [('Felipe', 'Molina'), ('Josefa', 'Espinoza'), ('Matías', 'Saavedra'), ('Trinidad', 'Navarro'), ('Agustín', 'Rojas')],
    'DEL-005': [('Camila', 'Bustos'), ('Lucas', 'Godoy'), ('Renata', 'Aguilera'), ('Sebastián', 'Tapia'), ('Fernanda', 'Muñoz')],
    'DEL-006': [('Valeria', 'Campos'), ('Gabriel', 'Silva'), ('Francisca', 'López'), ('Ignacio', 'Reyes'), ('Constanza', 'Pérez')],
}

ASSIGNMENTS = [
    ('Delegado Municipal', 'Delegado Municipal'),
    ('Gestor Territorial', 'Gestor Territorial'),
    ('Gestor Territorial', 'Gestor Territorial'),
    ('Verificador Técnico', 'Verificador Técnico'),
    ('Asistente Social', 'Gestor Territorial'),
]


class Command(BaseCommand):
    help = 'Crea cinco funcionarios ficticios @pnk.cl por delegación, sin contraseñas ni correos salientes.'

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError('Solo disponible en desarrollo (DEBUG=True).')
        delegations = {item.code: item for item in Delegation.objects.filter(
            code__in=SAMPLES, deleted_at__isnull=True, status='Activo'
        )}
        positions = {item.name: item for item in Position.objects.filter(
            deleted_at__isnull=True, status='Activo'
        )}
        roles = {item.name: item for item in Role.objects.filter(deleted_at__isnull=True)}
        if len(delegations) != len(SAMPLES) or any(
            position not in positions or role not in roles for position, role in ASSIGNMENTS
        ):
            raise CommandError('Faltan delegaciones, cargos o roles base; no se creó ninguna cuenta.')

        created = 0
        User = get_user_model()
        for delegation_index, (code, people) in enumerate(SAMPLES.items(), 1):
            delegation = delegations[code]
            for person_index, ((first, last), (position_name, role_name)) in enumerate(zip(people, ASSIGNMENTS), 1):
                serial = 98000000 + delegation_index * 100 + person_index
                username = f'muestra_sgr_{serial}'
                email = f'{first.lower()}.{last.lower()}.{serial}@pnk.cl'
                # ASCII para que el identificador no dependa de normalización Unicode.
                email = email.translate(str.maketrans('áéíóúñ', 'aeioun'))
                if User.objects.filter(username=username).exists() or UserProfile.objects.filter(email=email).exists():
                    existing = UserProfile.objects.filter(user__username=username, email=email, rut=example_rut(serial)).first()
                    if existing and existing.delegation_id == delegation.pk:
                        continue
                    raise CommandError(f'Colisión de identificador ficticio {username}; no se alteró la cuenta existente.')
                user = User(username=username, first_name=first, last_name=last, email=email, is_active=True)
                user.set_unusable_password()
                user.save()
                profile = UserProfile.objects.create(
                    user=user, rut=example_rut(serial), full_name=f'{first} {last}',
                    email=email, delegation=delegation, position=positions[position_name], status='Activo',
                )
                profile.roles.add(roles[role_name])
                created += 1
        self.stdout.write(self.style.SUCCESS(
            f'{created} cuentas ficticias creadas; cinco por delegación. No pueden iniciar sesión hasta que un administrador les asigne una clave.'
        ))
