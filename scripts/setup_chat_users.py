import os
import sys
from pathlib import Path

raise RuntimeError('Este generador antiguo está deshabilitado: debe adaptarse a roles por cargo y proteger las cuentas existentes antes de volver a utilizarse.')

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from django.contrib.auth import get_user_model
from organization.models import Delegation, Position, Role, UserProfile

User = get_user_model()

print("Configurando usuarios de prueba para el laboratorio de Chat y Channels...")

del_companias = Delegation.objects.filter(name__icontains='Compa').first() or Delegation.objects.first()
del_centro = Delegation.objects.filter(name__icontains='Centro').first() or Delegation.objects.last()

pos_gestor = Position.objects.filter(name__icontains='Gestor').first() or Position.objects.first()
role_gestor = Role.objects.filter(name__icontains='Gestor').first() or Role.objects.first()

test_users_data = [
    {
        'username': 'usuario_a',
        'rut': '11.111.111-1',
        'full_name': 'Usuario A (Las Compañías)',
        'email': 'usuario_a@laserena.cl',
        'delegation': del_companias,
        'position': pos_gestor,
        'role': role_gestor,
    },
    {
        'username': 'usuario_b',
        'rut': '22.222.222-2',
        'full_name': 'Usuario B (Las Compañías)',
        'email': 'usuario_b@laserena.cl',
        'delegation': del_companias,
        'position': pos_gestor,
        'role': role_gestor,
    },
    {
        'username': 'usuario_c',
        'rut': '33.333.333-3',
        'full_name': 'Usuario C (Centro Histórico)',
        'email': 'usuario_c@laserena.cl',
        'delegation': del_centro,
        'position': pos_gestor,
        'role': role_gestor,
    },
]

password = 'Inacap2026!'

for data in test_users_data:
    u, created = User.objects.get_or_create(
        username=data['username'],
        defaults={'email': data['email'], 'is_active': True}
    )
    u.set_password(password)
    u.is_active = True
    u.save()

    profile, _ = UserProfile.objects.get_or_create(
        user=u,
        defaults={
            'rut': data['rut'],
            'full_name': data['full_name'],
            'email': data['email'],
            'delegation': data['delegation'],
            'position': data['position'],
            'status': 'Activo',
        }
    )
    profile.delegation = data['delegation']
    profile.position = data['position']
    profile.status = 'Activo'
    profile.save()

    if data['role']:
        profile.roles.add(data['role'])

    print(f" -> {data['username']} listo | Org: {data['delegation'].name if data['delegation'] else 'N/A'} | Clave: {password}")

print("Usuarios creados exitosamente.")

