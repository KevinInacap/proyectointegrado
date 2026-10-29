import os
import sys
import django

# Setup Django environment if run as standalone script
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from datetime import date
from django.contrib.auth import get_user_model
from activities.models import Vecino, Activity, ServiceCatalog
from metrics.models import ManagementType, AttentionType, SubAttention, MeasurementItem, Goal, MeasurementPeriod
from organization.models import Position, Delegation, Role, UserProfile, PermissionDefinition
from organization.access import SUPER_ADMINISTRATOR_ROLE_NAME, SUPER_ADMINISTRATOR_RUT

User = get_user_model()

def seed():
    raise RuntimeError('Este generador antiguo está deshabilitado: debe adaptarse a roles por cargo y proteger las cuentas existentes antes de volver a utilizarse.')
    print("=== SEEDING EVALUATION OPERATIONAL RECORDS (>= 6 per catalog) ===")

    # 0. Ensure SuperAdministrador Role and User exist and are properly configured
    super_role, _ = Role.objects.get_or_create(
        name=SUPER_ADMINISTRATOR_ROLE_NAME,
        defaults={
            'description': 'Máxima autoridad institucional con facultades de administración global y eliminación de cuentas.',
            'is_system': True,
        }
    )
    if not super_role.is_system:
        super_role.is_system = True
        super_role.save(update_fields=['is_system'])

    # Assign all permission definitions to SuperAdministrador
    all_perms = PermissionDefinition.objects.all()
    if all_perms.exists():
        super_role.permission_definitions.set(all_perms)
        super_role.permissions_data = list(all_perms.values_list('code', flat=True))
        super_role.save()

    # Ensure SuperAdministrador Position exists
    super_pos, _ = Position.objects.get_or_create(
        name='SuperAdministrador',
        defaults={'description': 'Dirección Superior de la Plataforma SGR', 'status': 'Activo'}
    )

    # Assign SuperAdministrador to user with email keviinencinamolina2k20@gmail.com or RUT 21.571.404-7
    from django.db.models import Q
    target_user = User.objects.filter(
        Q(email__iexact='keviinencinamolina2k20@gmail.com') |
        Q(username__in=['kevinadmin', 'kevin_tulon', 'kevin']) |
        Q(profile__rut=SUPER_ADMINISTRATOR_RUT)
    ).first()

    if target_user:
        target_user.email = 'keviinencinamolina2k20@gmail.com'
        target_user.is_active = True
        target_user.save(update_fields=['email', 'is_active'])

        profile = getattr(target_user, 'profile', None)
        if not profile:
            profile, _ = UserProfile.objects.get_or_create(
                user=target_user,
                defaults={
                    'rut': SUPER_ADMINISTRATOR_RUT,
                    'full_name': 'Kevin Tulon Encina',
                    'email': 'keviinencinamolina2k20@gmail.com',
                    'status': 'Activo',
                    'position': super_pos
                }
            )
        profile.rut = SUPER_ADMINISTRATOR_RUT
        profile.email = 'keviinencinamolina2k20@gmail.com'
        profile.full_name = 'Kevin Tulon Encina'
        profile.status = 'Activo'
        profile.position = super_pos
        profile.save()
        profile.roles.add(super_role)
        print(f"SuperAdministrador assigned to: {profile.full_name} ({profile.user.username} - {profile.email} - {profile.rut})")

    # 1. Vecinos (at least 6)
    vecinos_data = [
        {"nombre": "Rosa Elena Villalobos", "rut": "14.892.314-5", "direccion": "Calle Balmaceda 1042", "territorio": "Delegación Centro Histórico", "estado": "Activo", "telefono": "+56984712033"},
        {"nombre": "Carlos Morales Pizarro", "rut": "16.241.879-2", "direccion": "Av. Islón 450", "territorio": "Delegación Las Compañías", "estado": "Activo", "telefono": "+56973129944"},
        {"nombre": "María Ignacia Cortés", "rut": "18.390.412-K", "direccion": "Los Corsarios 820", "territorio": "Delegación La Pampa", "estado": "Activo", "telefono": "+56991204855"},
        {"nombre": "Héctor Valenzuela Rojas", "rut": "12.784.561-3", "direccion": "Av. Cuatro Esquinas 1205", "territorio": "Delegación Avenida del Mar", "estado": "Activo", "telefono": "+56955412390"},
        {"nombre": "Patricia Andrea Vega", "rut": "15.632.198-4", "direccion": "Pasaje Los Naranjos 312", "territorio": "Delegación La Antena", "estado": "Activo", "telefono": "+56966847219"},
        {"nombre": "Jorge Alberto Cisternas", "rut": "11.450.982-1", "direccion": "Camino San Valentín s/n", "territorio": "Delegación Sector Rural", "estado": "Activo", "telefono": "+56944129850"},
    ]
    for vd in vecinos_data:
        v, created = Vecino.objects.get_or_create(
            rut=vd["rut"],
            defaults=vd
        )
        if created:
            print(f"Created Vecino: {v.nombre} ({v.rut})")

    # 2. Tipos de Gestión (at least 6)
    mgmt_data = [
        {"code": "GES-001-ING", "name": "Ingreso y Registro Inicial", "description": "Recepción y registro de solicitud del vecino", "status": "Activo"},
        {"code": "GES-002-EVA", "name": "Evaluación Social y Técnica", "description": "Análisis de antecedentes socioeconómicos y territoriales", "status": "Activo"},
        {"code": "GES-003-RES", "name": "Resolución y Entrega de Ayuda", "description": "Otorgamiento de prestación, subsidio o derivación formal", "status": "Activo"},
        {"code": "GES-004-TRT", "name": "Trámite Social Directo", "description": "Gestión directa de solicitudes y asistencias sociales inmediatas", "status": "Activo"},
        {"code": "GES-005-INS", "name": "Inspección Territorial", "description": "Levantamiento e inspección de terreno municipal", "status": "Activo"},
        {"code": "GES-006-SEG", "name": "Seguimiento de Caso", "description": "Monitoreo y fiscalización de compromisos comunitarios", "status": "Activo"},
    ]
    for md in mgmt_data:
        m, created = ManagementType.objects.get_or_create(
            code=md["code"],
            defaults=md
        )
        if created:
            print(f"Created ManagementType: {m.name} ({m.code})")

    # 3. Tipos de Atención (at least 6)
    att_types_data = [
        {"code": "TIP-001-ORI", "name": "Orientación Social y Familiar", "description": "Atención social integral a familias de la comuna", "status": "Activo"},
        {"code": "TIP-002-TER", "name": "Atención Territorial y Comunitaria", "description": "Gestión en terreno con juntas de vecinos y organizaciones", "status": "Activo"},
        {"code": "TIP-003-COM", "name": "Apoyo Comunitario y Emergencia", "description": "Asistencia ante emergencias sociales y climáticas", "status": "Activo"},
        {"code": "TIP-004-SUB", "name": "Subsidios y Beneficios Estatales", "description": "Atención y postulación a subsidios habitacionales y de agua potable", "status": "Activo"},
        {"code": "TIP-005-MED", "name": "Medio Ambiente y Espacios Verdes", "description": "Atención sobre microbasurales, podas y plazas vecinales", "status": "Activo"},
        {"code": "TIP-006-SEG", "name": "Seguridad Ciudadana e Iluminación", "description": "Requerimientos de luminarias y rondas preventivas comunitarias", "status": "Activo"},
    ]
    att_type_objs = {}
    for atd in att_types_data:
        at, created = AttentionType.objects.get_or_create(
            code=atd["code"],
            defaults=atd
        )
        att_type_objs[at.code] = at
        if created:
            print(f"Created AttentionType: {at.name} ({at.code})")

    # 4. Subatenciones (at least 6)
    sub_data = [
        {"code": "SUB-001-INF", "name": "Información del Registro Social de Hogares", "type_code": "TIP-001-ORI", "description": "Actualización y consulta de cartola RSH", "status": "Activo"},
        {"code": "SUB-002-CON", "name": "Consulta sobre Espacios Públicos", "type_code": "TIP-002-TER", "description": "Uso de sedes comunitarias y multicanchas", "status": "Activo"},
        {"code": "SUB-003-ORG", "name": "Orientación a Organizaciones Comunitarias", "type_code": "TIP-003-COM", "description": "Asesoría legal para directivas de juntas de vecinos", "status": "Activo"},
        {"code": "SUB-004-AGU", "name": "Subsidio de Agua Potable (SAP)", "type_code": "TIP-004-SUB", "description": "Postulación y renovación de subsidio de agua potable", "status": "Activo"},
        {"code": "SUB-005-PLA", "name": "Mantención de Áreas Verdes y Podas", "type_code": "TIP-005-MED", "description": "Poda de árboles en vía pública y mantención de plazas", "status": "Activo"},
        {"code": "SUB-006-LUM", "name": "Reparación de Alumbrado Público", "type_code": "TIP-006-SEG", "description": "Reporte de fallas en postes y luminarias barriales", "status": "Activo"},
    ]
    sub_objs = {}
    for sd in sub_data:
        parent_type = att_type_objs.get(sd["type_code"]) or AttentionType.objects.filter(code=sd["type_code"]).first() or AttentionType.objects.first()
        s, created = SubAttention.objects.get_or_create(
            code=sd["code"],
            defaults={
                "code": sd["code"],
                "name": sd["name"],
                "attention_type": parent_type,
                "description": sd["description"],
                "status": sd["status"]
            }
        )
        sub_objs[s.code] = s
        if created:
            print(f"Created SubAttention: {s.name} ({s.code})")

    # 5. Ítems de Medición (at least 6)
    item_data = [
        {"code": "ITM-001-ORI", "name": "Orientaciones Sociales Brindadas", "item_type": "Cuantitativo", "description": "Cantidad de atenciones sociales presenciales", "status": "Activo"},
        {"code": "ITM-002-TER", "name": "Reuniones Territoriales Realizadas", "item_type": "Cuantitativo", "description": "Mesas de trabajo y asambleas vecinales", "status": "Activo"},
        {"code": "ITM-003-COM", "name": "Ayudas Comunitarias Entregadas", "item_type": "Cuantitativo", "description": "Beneficios de emergencia otorgados a vecinos", "status": "Activo"},
        {"code": "ITM-004-SUB", "name": "Subsidios y Beneficios Tramitados", "item_type": "Cuantitativo", "description": "Cantidad de postulaciones a subsidios sociales ingresadas", "status": "Activo"},
        {"code": "ITM-005-AMB", "name": "Inspecciones Ambientales Realizadas", "item_type": "Cuantitativo", "description": "Inspecciones de terreno y microbasurales ejecutadas", "status": "Activo"},
        {"code": "ITM-006-SEG", "name": "Requerimientos de Seguridad Derivados", "item_type": "Cuantitativo", "description": "Casos derivados a Seguridad Ciudadana municipal", "status": "Activo"},
    ]
    item_objs = {}
    for idata in item_data:
        it, created = MeasurementItem.objects.get_or_create(
            code=idata["code"],
            defaults=idata
        )
        item_objs[it.code] = it
        if created:
            print(f"Created MeasurementItem: {it.name} ({it.code})")

    # 6. Período de Medición Garantizado
    period, _ = MeasurementPeriod.objects.get_or_create(
        name="Período Operativo 2026",
        defaults={
            "start_date": date(2026, 1, 1),
            "end_date": date(2026, 12, 31),
            "status": "Activo"
        }
    )

    # Cargos para Metas
    pos_asistente, _ = Position.objects.get_or_create(name="Asistente Social", defaults={"description": "Atención social directa"})
    pos_gestor, _ = Position.objects.get_or_create(name="Gestor Territorial", defaults={"description": "Gestión comunitaria"})
    pos_delegado, _ = Position.objects.get_or_create(name="Delegado Municipal", defaults={"description": "Coordinación de sede"})

    # 6. Metas (at least 6)
    goals_data = [
        {"code": "MET-001-ORI", "period": period, "position": pos_asistente, "item_code": "ITM-001-ORI", "target_value": 40.00, "weight": 20.00},
        {"code": "MET-002-TER", "period": period, "position": pos_gestor, "item_code": "ITM-002-TER", "target_value": 30.00, "weight": 20.00},
        {"code": "MET-003-COM", "period": period, "position": pos_delegado, "item_code": "ITM-003-COM", "target_value": 20.00, "weight": 15.00},
        {"code": "MET-004-SUB", "period": period, "position": pos_asistente, "item_code": "ITM-004-SUB", "target_value": 25.00, "weight": 15.00},
        {"code": "MET-005-AMB", "period": period, "position": pos_gestor, "item_code": "ITM-005-AMB", "target_value": 15.00, "weight": 15.00},
        {"code": "MET-006-SEG", "period": period, "position": pos_delegado, "item_code": "ITM-006-SEG", "target_value": 10.00, "weight": 15.00},
    ]
    for gd in goals_data:
        item_obj = item_objs.get(gd["item_code"]) or MeasurementItem.objects.filter(code=gd["item_code"]).first()
        if period and gd["position"] and item_obj:
            g, created = Goal.objects.get_or_create(
                code=gd["code"],
                defaults={
                    "period": period,
                    "position": gd["position"],
                    "item": item_obj,
                    "target_value": gd["target_value"],
                    "unit_of_measure": "Atenciones",
                    "weight": gd["weight"],
                    "status": "Activo"
                }
            )
            if created:
                print(f"Created Goal: {g.code} ({g.position} - {g.item})")

    # 7. Delegaciones
    del_centro, _ = Delegation.objects.get_or_create(name="Delegación Centro Histórico", defaults={"scope": "Centro", "commune": "La Serena"})
    del_companias, _ = Delegation.objects.get_or_create(name="Delegación Las Compañías", defaults={"scope": "Norte", "commune": "La Serena"})
    del_pampa, _ = Delegation.objects.get_or_create(name="Delegación La Pampa", defaults={"scope": "Sur", "commune": "La Serena"})
    del_antena, _ = Delegation.objects.get_or_create(name="Delegación La Antena", defaults={"scope": "Oriente", "commune": "La Serena"})
    del_mar, _ = Delegation.objects.get_or_create(name="Delegación Avenida del Mar", defaults={"scope": "Costero", "commune": "La Serena"})
    del_rural, _ = Delegation.objects.get_or_create(name="Delegación Sector Rural", defaults={"scope": "Rural", "commune": "La Serena"})

    admin_user = User.objects.filter(is_superuser=True).first() or User.objects.first()

    # 7. Atenciones (at least 6)
    atenciones_data = [
        {
            "activity_code": "AT-2026-001",
            "contact_name": "Rosa Elena Villalobos",
            "contact_phone": "+56984712033",
            "activity_date": date.today(),
            "delegation": del_centro,
            "type_code": "TIP-001-ORI",
            "sub_code": "SUB-001-INF",
            "item_code": "ITM-001-ORI",
            "problem_description": "Consulta sobre tramo del Registro Social de Hogares para postular a beneficios municipales.",
            "executed_action": "Se descarga cartola actualizada y se orienta respecto al proceso de apelación de ingresos.",
            "validation_status": "Approved"
        },
        {
            "activity_code": "AT-2026-002",
            "contact_name": "Carlos Morales Pizarro",
            "contact_phone": "+56973129944",
            "activity_date": date.today(),
            "delegation": del_companias,
            "type_code": "TIP-002-TER",
            "sub_code": "SUB-002-CON",
            "item_code": "ITM-002-TER",
            "problem_description": "Solicita autorización de uso de sede vecinal para taller comunitario de personas mayores.",
            "executed_action": "Se coordina con encargado territorial y se agenda espacio en calendario municipal.",
            "validation_status": "Approved"
        },
        {
            "activity_code": "AT-2026-003",
            "contact_name": "Jorge Alberto Cisternas",
            "contact_phone": "+56944129850",
            "activity_date": date.today(),
            "delegation": del_rural,
            "type_code": "TIP-003-COM",
            "sub_code": "SUB-003-ORG",
            "item_code": "ITM-003-COM",
            "problem_description": "Solicita apoyo de asesoría jurídica para renovación de directiva de junta de vecinos rural.",
            "executed_action": "Se recepciona acta de asamblea y se entrega guía de estatutos municipales.",
            "validation_status": "Approved"
        },
        {
            "activity_code": "AT-2026-004",
            "contact_name": "Patricia Andrea Vega",
            "contact_phone": "+56966847219",
            "activity_date": date.today(),
            "delegation": del_antena,
            "type_code": "TIP-004-SUB",
            "sub_code": "SUB-004-AGU",
            "item_code": "ITM-004-SUB",
            "problem_description": "Solicita postulación al subsidio de agua potable por aumento en tarifa mensual.",
            "executed_action": "Se revisa ficha social en RSH y se ingresa formulario de postulación a SAP.",
            "validation_status": "Approved"
        },
        {
            "activity_code": "AT-2026-005",
            "contact_name": "Héctor Valenzuela Rojas",
            "contact_phone": "+56955412390",
            "activity_date": date.today(),
            "delegation": del_mar,
            "type_code": "TIP-005-MED",
            "sub_code": "SUB-005-PLA",
            "item_code": "ITM-005-AMB",
            "problem_description": "Solicita poda urgente de ramas sobre cables eléctricos en Av. Cuatro Esquinas.",
            "executed_action": "Se genera orden de trabajo y se deriva a cuadrilla de Operaciones.",
            "validation_status": "Pending"
        },
        {
            "activity_code": "AT-2026-006",
            "contact_name": "María Ignacia Cortés",
            "contact_phone": "+56991204855",
            "activity_date": date.today(),
            "delegation": del_pampa,
            "type_code": "TIP-006-SEG",
            "sub_code": "SUB-006-LUM",
            "item_code": "ITM-006-SEG",
            "problem_description": "Informa luminarias apagadas en pasaje Los Corsarios generando inseguridad nocturna.",
            "executed_action": "Se remite folio a inspector de alumbrado público para reposición de luminaria LED.",
            "validation_status": "Approved"
        },
    ]
    for ad in atenciones_data:
        att_type = att_type_objs.get(ad["type_code"]) or AttentionType.objects.filter(code=ad["type_code"]).first()
        sub_att = sub_objs.get(ad["sub_code"]) or SubAttention.objects.filter(code=ad["sub_code"]).first()
        itm = item_objs.get(ad["item_code"]) or MeasurementItem.objects.filter(code=ad["item_code"]).first()
        act, created = Activity.objects.get_or_create(
            activity_code=ad["activity_code"],
            defaults={
                "activity_code": ad["activity_code"],
                "contact_name": ad["contact_name"],
                "contact_phone": ad["contact_phone"],
                "activity_date": ad["activity_date"],
                "delegation": ad["delegation"],
                "attention_type": att_type,
                "subattention": sub_att,
                "period": period,
                "item": itm,
                "problem_description": ad["problem_description"],
                "executed_action": ad["executed_action"],
                "validation_status": ad["validation_status"],
                "user": admin_user
            }
        )
        if created:
            print(f"Created Activity: {act.activity_code} ({act.contact_name})")

    # 8. Catálogo de Servicios (ServiceCatalog, at least 6)
    service_data = [
        {"area": "DIDECO", "service": "Orientación Social", "attention_type": "Orientación Social y Familiar", "subattention_type": "Información del Registro Social de Hogares", "status": "Activo"},
        {"area": "Territorial", "service": "Gestión Vecinal", "attention_type": "Atención Territorial y Comunitaria", "subattention_type": "Consulta sobre Espacios Públicos", "status": "Activo"},
        {"area": "Comunitario", "service": "Apoyo de Emergencia", "attention_type": "Apoyo Comunitario y Emergencia", "subattention_type": "Orientación a Organizaciones Comunitarias", "status": "Activo"},
        {"area": "DIDECO", "service": "Subsidios Estatales", "attention_type": "Subsidios y Beneficios Estatales", "subattention_type": "Subsidio de Agua Potable (SAP)", "status": "Activo"},
        {"area": "Medio Ambiente", "service": "Mantención de Espacios Públicos", "attention_type": "Medio Ambiente y Espacios Verdes", "subattention_type": "Mantención de Áreas Verdes y Podas", "status": "Activo"},
        {"area": "Seguridad", "service": "Infraestructura Urbana Segura", "attention_type": "Seguridad Ciudadana e Iluminación", "subattention_type": "Reparación de Alumbrado Público", "status": "Activo"},
    ]
    for sdata in service_data:
        sc, created = ServiceCatalog.objects.get_or_create(
            area=sdata["area"],
            service=sdata["service"],
            attention_type=sdata["attention_type"],
            defaults=sdata
        )
        if created:
            print(f"Created ServiceCatalog: {sc.service}")

    print("\n--- FINAL COUNTS ---")
    print("Vecinos:", Vecino.objects.count())
    print("ManagementType:", ManagementType.objects.count())
    print("AttentionType:", AttentionType.objects.count())
    print("SubAttention:", SubAttention.objects.count())
    print("MeasurementItem:", MeasurementItem.objects.count())
    print("Goal:", Goal.objects.count())
    print("Activity:", Activity.objects.count())
    print("ServiceCatalog:", ServiceCatalog.objects.count())
    print("=== SEEDING COMPLETED SUCCESSFULLY ===")

if __name__ == '__main__':
    seed()
