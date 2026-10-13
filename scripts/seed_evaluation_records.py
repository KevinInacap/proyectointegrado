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
    print("=== SEEDING EVALUATION OPERATIONAL RECORDS ===")

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

    # Assign SuperAdministrador to user with RUT 21.571.404-7
    target_profile = UserProfile.objects.filter(rut=SUPER_ADMINISTRATOR_RUT).first()
    if target_profile:
        target_profile.roles.add(super_role)
        target_profile.position = super_pos
        target_profile.save()
        print(f"SuperAdministrador assigned to: {target_profile.full_name} ({target_profile.rut})")
    else:
        # Check if user kevin_tulon exists and link profile
        target_user = User.objects.filter(username='kevin_tulon').first()
        if target_user:
            profile, _ = UserProfile.objects.get_or_create(
                user=target_user,
                defaults={
                    'rut': SUPER_ADMINISTRATOR_RUT,
                    'full_name': 'Kevin Tulon',
                    'email': target_user.email or 'kevin@laserena.cl',
                    'status': 'Activo',
                    'position': super_pos
                }
            )
            profile.roles.add(super_role)
            print(f"Profile created and SuperAdministrador assigned to: {profile.full_name} ({profile.rut})")

    # 1. Vecinos (at least 6)
    vecinos_data = [
        {"nombre": "Rosa Elena Villalobos", "rut": "14.892.314-5", "direccion": "Calle Balmaceda 1042", "territorio": "Delegación Centro Histórico", "estado": "Activo", "telefono": "+56984712033"},
        {"nombre": "Carlos Morales Pizarro", "rut": "16.241.879-2", "direccion": "Av. Islón 450", "territorio": "Delegación Las Compañías", "estado": "Activo", "telefono": "+56973129944"},
        {"nombre": "María Ignacia Cortés", "rut": "18.390.412-K", "direccion": "Los Corsarios 820", "territorio": "Delegación La Pampa", "estado": "Activo", "telefono": "+56991204855"},
        {"nombre": "Héctor Valenzuela Rojas", "rut": "12.784.561-3", "direccion": "Av. Cuatro Esquinas 1205", "territorio": "Delegación Avenida del Mar", "estado": "Activo", "telefono": "+56955412390"},
        {"nombre": "Patricia Andrea Vega", "rut": "15.632.198-4", "direccion": "Pasaje Los Naranjos 312", "territorio": "Delegación La Antena", "estado": "Activo", "telefono": "+56966847219"},
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
    tip_sub = AttentionType.objects.filter(code="TIP-004-SUB").first()
    tip_med = AttentionType.objects.filter(code="TIP-005-MED").first()
    tip_seg = AttentionType.objects.filter(code="TIP-006-SEG").first()
    fallback_type = AttentionType.objects.first()

    sub_data = [
        {"code": "SUB-004-AGU", "name": "Subsidio de Agua Potable (SAP)", "attention_type": tip_sub or fallback_type, "description": "Postulación y renovación de subsidio de agua potable", "status": "Activo"},
        {"code": "SUB-005-PLA", "name": "Mantención de Áreas Verdes y Podas", "attention_type": tip_med or fallback_type, "description": "Poda de árboles en vía pública y mantención de plazas", "status": "Activo"},
        {"code": "SUB-006-LUM", "name": "Reparación de Alumbrado Público", "attention_type": tip_seg or fallback_type, "description": "Reporte de fallas en postes y luminarias barriales", "status": "Activo"},
    ]
    sub_objs = {}
    for sd in sub_data:
        s, created = SubAttention.objects.get_or_create(
            code=sd["code"],
            defaults=sd
        )
        sub_objs[s.code] = s
        if created:
            print(f"Created SubAttention: {s.name} ({s.code})")

    # 5. Ítems de Medición (at least 6)
    item_data = [
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

    # 6. Metas (at least 6)
    period = MeasurementPeriod.objects.first()
    pos_asistente = Position.objects.filter(name="Asistente Social").first() or Position.objects.first()
    pos_gestor = Position.objects.filter(name="Gestor Territorial").first() or Position.objects.first()
    pos_delegado = Position.objects.filter(name="Delegado Municipal").first() or Position.objects.first()

    goals_data = [
        {
            "code": "MET-004-SUB",
            "period": period,
            "position": pos_asistente,
            "item": item_objs.get("ITM-004-SUB") or MeasurementItem.objects.filter(code="ITM-004-SUB").first(),
            "target_value": 25.00,
            "unit_of_measure": "Atenciones",
            "weight": 30.00,
            "status": "Activo"
        },
        {
            "code": "MET-005-AMB",
            "period": period,
            "position": pos_gestor,
            "item": item_objs.get("ITM-005-AMB") or MeasurementItem.objects.filter(code="ITM-005-AMB").first(),
            "target_value": 15.00,
            "unit_of_measure": "Atenciones",
            "weight": 20.00,
            "status": "Activo"
        },
        {
            "code": "MET-006-SEG",
            "period": period,
            "position": pos_delegado,
            "item": item_objs.get("ITM-006-SEG") or MeasurementItem.objects.filter(code="ITM-006-SEG").first(),
            "target_value": 10.00,
            "unit_of_measure": "Atenciones",
            "weight": 25.00,
            "status": "Activo"
        },
    ]
    for gd in goals_data:
        if gd["period"] and gd["position"] and gd["item"]:
            g, created = Goal.objects.get_or_create(
                period=gd["period"],
                position=gd["position"],
                item=gd["item"],
                defaults={
                    "code": gd["code"],
                    "target_value": gd["target_value"],
                    "unit_of_measure": gd["unit_of_measure"],
                    "weight": gd["weight"],
                    "status": gd["status"]
                }
            )
            if created:
                print(f"Created Goal: {g.code} ({g.position} - {g.item})")

    # 7. Atenciones (Activity, at least 6)
    del_centro = Delegation.objects.filter(name__icontains="Centro").first()
    del_companias = Delegation.objects.filter(name__icontains="Compa").first()
    del_pampa = Delegation.objects.filter(name__icontains="Pampa").first()
    admin_user = User.objects.filter(is_superuser=True).first() or User.objects.first()

    atenciones_data = [
        {
            "activity_code": "AT-2026-004",
            "contact_name": "Rosa Elena Villalobos",
            "contact_phone": "+56984712033",
            "activity_date": date.today(),
            "delegation": del_centro,
            "attention_type": tip_sub or AttentionType.objects.first(),
            "subattention": sub_objs.get("SUB-004-AGU") or SubAttention.objects.first(),
            "period": period,
            "item": item_objs.get("ITM-004-SUB") or MeasurementItem.objects.first(),
            "problem_description": "Solicita postulación al subsidio de agua potable por aumento en tarifa mensual.",
            "executed_action": "Se revisa ficha social en RSH y se ingresa formulario de postulación a SAP.",
            "validation_status": "Approved",
            "user": admin_user
        },
        {
            "activity_code": "AT-2026-005",
            "contact_name": "Carlos Morales Pizarro",
            "contact_phone": "+56973129944",
            "activity_date": date.today(),
            "delegation": del_companias,
            "attention_type": tip_med or AttentionType.objects.first(),
            "subattention": sub_objs.get("SUB-005-PLA") or SubAttention.objects.first(),
            "period": period,
            "item": item_objs.get("ITM-005-AMB") or MeasurementItem.objects.first(),
            "problem_description": "Solicita poda urgente de ramas sobre cables eléctricos en calle Islón.",
            "executed_action": "Se genera orden de trabajo y se deriva a cuadrilla de Operaciones.",
            "validation_status": "Pending",
            "user": admin_user
        },
        {
            "activity_code": "AT-2026-006",
            "contact_name": "María Ignacia Cortés",
            "contact_phone": "+56991204855",
            "activity_date": date.today(),
            "delegation": del_pampa,
            "attention_type": tip_seg or AttentionType.objects.first(),
            "subattention": sub_objs.get("SUB-006-LUM") or SubAttention.objects.first(),
            "period": period,
            "item": item_objs.get("ITM-006-SEG") or MeasurementItem.objects.first(),
            "problem_description": "Informa luminarias apagadas en pasaje Los Corsarios generando inseguridad nocturna.",
            "executed_action": "Se remite folio a inspector de alumbrado público para reposición de luminaria LED.",
            "validation_status": "Approved",
            "user": admin_user
        },
    ]
    for ad in atenciones_data:
        act, created = Activity.objects.get_or_create(
            activity_code=ad["activity_code"],
            defaults=ad
        )
        if created:
            print(f"Created Activity: {act.activity_code} ({act.contact_name})")

    # 8. Catálogo de Servicios (ServiceCatalog)
    service_data = [
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
