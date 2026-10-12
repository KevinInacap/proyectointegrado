"""Prepara una base MySQL aislada para pruebas manuales; no modifica la base habitual.

Ejecutar desde la raíz con el Python del proyecto. La clave temporal solo se imprime
en la terminal local; no se incluye en informes ni debe compartirse en Git.
"""
import json
import os
from pathlib import Path
import secrets
import sys
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
os.environ['DEBUG'] = 'True'
os.environ['EMAIL_HOST_PASSWORD'] = ''

import django
django.setup()
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import connection
from organization.models import Delegation, Position, Role, UserProfile
from metrics.models import MeasurementItem, AttentionType, SubAttention

if connection.vendor != 'mysql':
    raise SystemExit('El laboratorio exige una conexión local MySQL.')
if connection.settings_dict['HOST'] not in ('127.0.0.1', 'localhost'):
    raise SystemExit('Solo se permite la base del equipo local.')
name = 'sgr_qa_' + datetime.now().strftime('%Y%m%d_%H%M%S')
with connection.cursor() as cursor:
    cursor.execute(f'CREATE DATABASE `{name}` CHARACTER SET utf8mb4')
connection.close()
settings.DATABASES['default']['NAME'] = name
connection.settings_dict['NAME'] = name
call_command('migrate', verbosity=0)
call_command('seed_data', verbosity=0)
password = secrets.token_urlsafe(18) + 'Aa7!'
delegations = list(Delegation.objects.order_by('pk'))
accounts = []
names = ['Diego Ensayo', 'Felipe Ensayo', 'Jorge Ensayo', 'Scarlett Ensayo', 'Elena Ensayo', 'Camila Ensayo', 'Pedro Ensayo', 'María Ensayo']
positions = ['Administrador General', 'Coordinador del Sistema', 'Delegado Municipal',
             'Gestor Territorial', 'Verificador Técnico', 'Asistente Social', 'Auditor Municipal', 'Usuario de Consulta']
for index, position_name in enumerate(positions):
    position, _ = Position.objects.get_or_create(name=position_name)
    role = Role.objects.get(name='Administrador') if not index else Role.objects.create(
        name=f'Ensayo {position_name}'[:50], permissions_data=['lectura', 'edicion', 'derivacion', 'cierre'])
    username = f'qa{index}'
    user = get_user_model().objects.create_user(username, f'{username}@example.test', password)
    rut_body = str(91000000 + index)
    remainder = 11 - sum(int(digit) * (2 + i % 6) for i, digit in enumerate(reversed(rut_body))) % 11
    verifier = '0' if remainder == 11 else 'K' if remainder == 10 else str(remainder)
    profile = UserProfile.objects.create(user=user, rut=f'{rut_body}-{verifier}', full_name=names[index],
        email=f'{username}@example.test', delegation=delegations[index % len(delegations)], position=position)
    profile.roles.add(role)
    accounts.append({'username': username, 'cargo': position_name})
for index in range(13):
    MeasurementItem.objects.create(code=f'QA-IT-{index:02d}', name=f'Ítem de ensayo {index:02d}', description='Registro sintético para paginación y exportación')
kind = AttentionType.objects.create(code='QA-TIPO', name='Orientación de ensayo', description='Catálogo de laboratorio')
SubAttention.objects.create(code='QA-SUB', name='Consulta de ensayo', attention_type=kind)
print(json.dumps({'database': name, 'password': password, 'accounts': accounts}, ensure_ascii=False))
