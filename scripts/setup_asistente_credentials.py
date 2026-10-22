import os
import sys
from pathlib import Path
from datetime import date

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Setup Django with current .env
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from django.contrib.auth import get_user_model
from organization.models import Delegation, Position, Role, UserProfile
from social.models import SocialCase, SocialManagement
from activities.models import ServiceCatalog

print("=== CONFIGURANDO USUARIO Y DATOS PARA ASISTENTE SOCIAL ===")

User = get_user_model()
del_centro = Delegation.objects.filter(name__icontains='Centro').first() or Delegation.objects.filter(status='Activo').first()
pos_asistente, _ = Position.objects.get_or_create(
    name='Asistente Social',
    defaults={'description': 'Atención social y levantamiento de fichas socioeconómicas', 'status': 'Activo'}
)
role_gestor = Role.objects.filter(name__in=['Gestor Territorial', 'Funcionario / Gestor']).first() or Role.objects.filter(status='Activo').first()

# 1. Crear o actualizar usuario
asist_user, created = User.objects.get_or_create(
    username='asistente',
    defaults={
        'email': 'asistente@laserena.cl',
        'first_name': 'Camila',
        'last_name': 'Rojas',
        'is_active': True
    }
)
asist_user.set_password('asistente123')
asist_user.is_active = True
asist_user.save()

# 2. Perfil institucional
profile, p_created = UserProfile.objects.get_or_create(
    user=asist_user,
    defaults={
        'rut': '18.420.915-K',
        'full_name': 'Camila Francisca Rojas Silva',
        'email': 'asistente@laserena.cl',
        'delegation': del_centro,
        'position': pos_asistente,
        'status': 'Activo'
    }
)
if profile.position != pos_asistente:
    profile.position = pos_asistente
if del_centro and profile.delegation != del_centro:
    profile.delegation = del_centro
profile.status = 'Activo'
profile.save()

if role_gestor and role_gestor not in profile.roles.all():
    profile.roles.add(role_gestor)

print("-> Usuario Django 'asistente' listo con contraseña 'asistente123'.")
print("-> Cargo:", pos_asistente.name, "· Delegación:", del_centro.name if del_centro else "Central")

# 3. Cargar casos sociales de demostración
catalogs = list(ServiceCatalog.objects.filter(status='Activo'))
cat_subsidio = catalogs[0] if catalogs else None

casos_data = [
    {
        'rut': '14.892.314-5', 'nombre': 'Rosa Elena Villalobos', 'phone': '+56 9 8451 2210',
        'etapas': [
            (1, 'Ingreso y recepción de antecedentes', 'Se recepciona solicitud por situación de emergencia habitacional y vulnerabilidad extrema.'),
            (2, 'Visita en terreno y levantamiento técnico', '[Respaldo: EVI-202610-A19] Constatación en terreno de filtraciones severas en techumbre de vivienda social en Sector Centro.'),
            (3, 'Resolución y entrega de subsidio', '[Subsidio/Prestación: Materiales de Construcción y Techumbre] Entrega de 12 planchas de zinc y kit de aislamiento DIDECO.')
        ]
    },
    {
        'rut': '16.241.879-2', 'nombre': 'Carlos Morales Pizarro', 'phone': '+56 9 7712 4433',
        'etapas': [
            (1, 'Ingreso y recepción de antecedentes', 'Ingreso por desempleo prolongado y solicitud de subsidio de agua potable (SAP).'),
            (2, 'Visita en terreno y levantamiento técnico', '[Respaldo: EVI-202610-B42] Inspección domiciliaria y verificación de colillas de cobro Aguas del Valle.')
        ]
    },
    {
        'rut': '18.390.412-K', 'nombre': 'María Ignacia Cortés', 'phone': '+56 9 9123 7845',
        'etapas': [
            (1, 'Ingreso y recepción de antecedentes', 'Solicitud de canasta de alimentos de emergencia y orientación programa familias.')
        ]
    },
    {
        'rut': '12.784.561-3', 'nombre': 'Héctor Valenzuela Rojas', 'phone': '+56 9 6543 2198',
        'etapas': [
            (1, 'Ingreso y recepción de antecedentes', 'Adulto mayor dependiente severo requiere postulación a ayuda técnica y exención de aseo.'),
            (2, 'Visita en terreno y levantamiento técnico', '[Respaldo: EVI-202610-C77] Evaluación de redes de apoyo familiares y barreras arquitectónicas.'),
            (3, 'Resolución y entrega de subsidio', '[Subsidio/Prestación: Ayuda Técnica y Exención Derechos de Aseo] Aprobación de silla de ruedas ortopédica y decreto de exención.')
        ]
    },
    {
        'rut': '15.632.198-4', 'nombre': 'Patricia Andrea Vega', 'phone': '+56 9 5567 8901',
        'etapas': [
            (1, 'Ingreso y recepción de antecedentes', 'Madre jefa de hogar con 3 hijos menores en edad escolar, requiere subsidio asistencial.')
        ]
    }
]

for cd in casos_data:
    c, c_created = SocialCase.objects.get_or_create(
        user_rut=cd['rut'],
        defaults={
            'user_name': cd['nombre'],
            'contact_phone': cd['phone'],
            'delegation': del_centro,
            'entry_date': date(2026, 9, 15)
        }
    )
    for stage_num, mgmt_type, res in cd['etapas']:
        SocialManagement.objects.get_or_create(
            case=c,
            stage=stage_num,
            defaults={
                'catalog': cat_subsidio,
                'management_type': mgmt_type,
                'management_date': date(2026, 9, 15 + stage_num * 5),
                'result': res
            }
        )

print(f"-> Casos sociales en base de datos: {SocialCase.objects.count()}")
print(f"-> Gestiones de 3 etapas en base de datos: {SocialManagement.objects.count()}")
print("=== CONFIGURACIÓN FINALIZADA EXITOSAMENTE ===")
