import os
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Setup Django with current .env
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from django.db import connection
from django.contrib.auth import get_user_model
from organization.models import Delegation, Position, Role, UserProfile

print("1. Configurando usuario en MySQL (admin / admin)...")
with connection.cursor() as cursor:
    cursor.execute("CREATE USER IF NOT EXISTS 'admin'@'localhost' IDENTIFIED BY 'admin';")
    cursor.execute("ALTER USER 'admin'@'localhost' IDENTIFIED BY 'admin';")
    cursor.execute("GRANT ALL PRIVILEGES ON *.* TO 'admin'@'localhost' WITH GRANT OPTION;")
    
    cursor.execute("CREATE USER IF NOT EXISTS 'admin'@'127.0.0.1' IDENTIFIED BY 'admin';")
    cursor.execute("ALTER USER 'admin'@'127.0.0.1' IDENTIFIED BY 'admin';")
    cursor.execute("GRANT ALL PRIVILEGES ON *.* TO 'admin'@'127.0.0.1' WITH GRANT OPTION;")
    
    # También actualizamos root por si acaso
    cursor.execute("ALTER USER 'root'@'localhost' IDENTIFIED BY 'admin';")
    try:
        cursor.execute("ALTER USER 'root'@'127.0.0.1' IDENTIFIED BY 'admin';")
    except Exception:
        pass
    
    cursor.execute("FLUSH PRIVILEGES;")
print("-> Usuario MySQL 'admin' y 'root' configurados con contraseña 'admin'.")

print("2. Configurando usuario superadministrador en Django (admin / admin)...")
User = get_user_model()
admin_user, created = User.objects.get_or_create(username='admin')
admin_user.set_password('admin')
admin_user.is_superuser = True
admin_user.is_staff = True
admin_user.email = 'admin@sgr.local'
admin_user.save()

# Asegurar perfil de organización para 'admin'
delegation = Delegation.objects.filter(status='Activo').first()
position = Position.objects.filter(status='Activo').first()
admin_role = Role.objects.filter(name='Administrador').first()

profile, p_created = UserProfile.objects.get_or_create(
    user=admin_user,
    defaults={
        'rut': '11111111-1',
        'full_name': 'Administrador General',
        'email': 'admin@sgr.local',
        'delegation': delegation,
        'position': position,
        'status': 'Activo'
    }
)
if admin_role and admin_role not in profile.roles.all():
    profile.roles.add(admin_role)

# También actualizar contraseña de pnkadmin a 'admin'
if User.objects.filter(username='pnkadmin').exists():
    pnk = User.objects.get(username='pnkadmin')
    pnk.set_password('admin')
    pnk.save()
    print("-> Usuario 'pnkadmin' también actualizado con contraseña 'admin'.")

print("-> Usuario Django 'admin' listo con contraseña 'admin' y rol 'Administrador'.")
