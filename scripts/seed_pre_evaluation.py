import os
import sys
import django

# Setup Django environment
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from datetime import date
from django.contrib.auth import get_user_model
from activities.models import Vecino, Activity, ServiceCatalog
from metrics.models import ManagementType, AttentionType, SubAttention, MeasurementItem, Goal, MeasurementPeriod
from organization.models import Position, Delegation, Role, UserProfile, PermissionDefinition
from organization.access import ADMINISTRATOR_ROLE_NAME, SUPER_ADMINISTRATOR_ROLE_NAME, set_role_permission_codes
from social.models import SocialCase, SocialManagement

User = get_user_model()

def seed_pre_evaluation():
    raise RuntimeError('Este generador antiguo está deshabilitado: debe adaptarse a roles por cargo y proteger las cuentas existentes antes de volver a utilizarse.')
    print("=" * 65)
    print("  SEEDING PRE-EVALUACIÓN SUMATIVA III — LA SERENA 2026")
    print("=" * 65)

    # 1. ROLES DEL SISTEMA CON PERMISOS COMPLETOS
    all_perms = list(PermissionDefinition.objects.all())
    perm_codes = list(PermissionDefinition.objects.values_list('code', flat=True)) or ['lectura', 'edicion', 'derivacion', 'cierre']

    admin_role, _ = Role.objects.get_or_create(
        name=ADMINISTRATOR_ROLE_NAME,
        defaults={
            'description': 'Administrador institucional con control completo sobre mantenedores y registros.',
            'is_system': True,
            'permissions_data': perm_codes
        }
    )
    admin_role.permissions_data = perm_codes
    admin_role.save()
    if all_perms:
        admin_role.permission_definitions.set(all_perms)

    super_role, _ = Role.objects.get_or_create(
        name=SUPER_ADMINISTRATOR_ROLE_NAME,
        defaults={
            'description': 'Superadministrador con facultades globales.',
            'is_system': True,
            'permissions_data': perm_codes
        }
    )
    super_role.permissions_data = perm_codes
    super_role.save()
    if all_perms:
        super_role.permission_definitions.set(all_perms)

    asistente_role, _ = Role.objects.get_or_create(
        name='Asistente Social',
        defaults={
            'description': 'Gestión de casos sociales, fichas de vecinos y atenciones en territorio.',
            'is_system': True,
            'permissions_data': ['lectura', 'edicion', 'derivacion', 'cierre']
        }
    )
    set_role_permission_codes(asistente_role, ['lectura', 'edicion', 'derivacion', 'cierre'])

    delegado_role, _ = Role.objects.get_or_create(
        name='Delegado Municipal',
        defaults={
            'description': 'Jefatura territorial de delegación municipal con control operativo de atenciones.',
            'is_system': True,
            'permissions_data': ['lectura', 'edicion', 'derivacion', 'cierre']
        }
    )
    set_role_permission_codes(delegado_role, ['lectura', 'edicion', 'derivacion', 'cierre'])

    # 2. LAS 6 DELEGACIONES TERRITORIALES OFICIALES DE LA SERENA
    delegaciones_data = [
        {"name": "Delegación Avenida del Mar", "scope": "Costero", "commune": "La Serena", "address": "Av. del Mar 2500", "status": "Activo"},
        {"name": "Delegación Centro Histórico", "scope": "Centro", "commune": "La Serena", "address": "Cienfuegos 226", "status": "Activo"},
        {"name": "Delegación Las Compañías", "scope": "Norte", "commune": "La Serena", "address": "Esmeralda 2422", "status": "Activo"},
        {"name": "Delegación La Pampa", "scope": "Sur", "commune": "La Serena", "address": "Larraín Alcalde 3505", "status": "Activo"},
        {"name": "Delegación La Antena", "scope": "Oriente", "commune": "La Serena", "address": "Av. 18 de Septiembre S/N", "status": "Activo"},
        {"name": "Delegación Sector Rural", "scope": "Rural", "commune": "La Serena", "address": "O'Higgins 154", "status": "Activo"},
    ]
    del_objs = {}
    for dd in delegaciones_data:
        d, _ = Delegation.objects.get_or_create(name=dd["name"], defaults=dd)
        d.scope = dd["scope"]
        d.address = dd["address"]
        d.status = "Activo"
        d.deleted_at = None
        d.save()
        del_objs[d.name] = d
        print(f"  [OK] Delegación: {d.name} ({d.scope})")

    # 3. CARGOS MUNICIPALES
    pos_asistente, _ = Position.objects.get_or_create(name="Asistente Social", defaults={"description": "Atención social y visitas domiciliarias DIDECO", "status": "Activo"})
    pos_admin, _ = Position.objects.get_or_create(name="Administrador General", defaults={"description": "Coordinación y gestión de la plataforma SGR", "status": "Activo"})
    pos_super, _ = Position.objects.get_or_create(name="SuperAdministrador", defaults={"description": "Dirección superior y gobernanza SGR", "status": "Activo"})
    pos_gestor, _ = Position.objects.get_or_create(name="Gestor Territorial", defaults={"description": "Gestión vecinal y comunitaria en terreno", "status": "Activo"})
    pos_delegado, _ = Position.objects.get_or_create(name="Delegado Municipal", defaults={"description": "Jefatura territorial de sede municipal", "status": "Activo"})

    for p in (pos_asistente, pos_admin, pos_super, pos_gestor, pos_delegado):
        p.status = 'Activo'
        p.deleted_at = None
        p.save()

    # 4. CUENTAS DE USUARIO CLAVE PARA LA EVALUACIÓN
    # 4.1 Scarlett Williams (Asistente Social + Rol Administrador para control de mantenedores)
    u_scarlett, _ = User.objects.get_or_create(username='scarlett')
    u_scarlett.set_password('Admin123!')
    u_scarlett.first_name = 'Scarlett'
    u_scarlett.last_name = 'Williams Medalla'
    u_scarlett.email = 'scarlett.williams@laserena.cl'
    u_scarlett.is_active = True
    u_scarlett.is_staff = True
    u_scarlett.save()

    p_scarlett, _ = UserProfile.objects.get_or_create(user=u_scarlett)
    p_scarlett.full_name = 'Scarlett Williams Medalla'
    p_scarlett.rut = '19.822.450-3'
    p_scarlett.email = 'scarlett.williams@laserena.cl'
    p_scarlett.phone = '+56 9 7889 0012'
    p_scarlett.position = pos_asistente
    p_scarlett.delegation = del_objs["Delegación Avenida del Mar"]
    p_scarlett.status = 'Activo'
    p_scarlett.deleted_at = None
    p_scarlett.save()
    p_scarlett.roles.set([asistente_role])
    print(f"  [USER] scarlett -> Password: Admin123! (Cargo: Asistente Social · Delegación Avenida del Mar)")

    # 4.1B Delegado Municipal (Delegación Avenida del Mar)
    u_delegado, _ = User.objects.get_or_create(username='delegado')
    u_delegado.set_password('Admin123!')
    u_delegado.first_name = 'Roberto'
    u_delegado.last_name = 'Campusano Rojas'
    u_delegado.email = 'delegado.avenidadelmar@laserena.cl'
    u_delegado.is_active = True
    u_delegado.is_staff = False
    u_delegado.save()

    p_delegado, _ = UserProfile.objects.get_or_create(user=u_delegado)
    p_delegado.full_name = 'Roberto Campusano Rojas'
    p_delegado.rut = '14.521.890-2'
    p_delegado.email = 'delegado.avenidadelmar@laserena.cl'
    p_delegado.phone = '+56 9 8765 4321'
    p_delegado.position = pos_delegado
    p_delegado.delegation = del_objs["Delegación Avenida del Mar"]
    p_delegado.status = 'Activo'
    p_delegado.deleted_at = None
    p_delegado.save()
    p_delegado.roles.set([delegado_role])
    print(f"  [USER] delegado -> Password: Admin123! (Cargo: Delegado Municipal · Delegación Avenida del Mar)")

    # 4.2 Administrador General
    u_admin, _ = User.objects.get_or_create(username='admin')
    u_admin.set_password('Admin123!')
    u_admin.first_name = 'Administrador'
    u_admin.last_name = 'General'
    u_admin.email = 'admin@laserena.cl'
    u_admin.is_active = True
    u_admin.is_staff = True
    u_admin.is_superuser = True
    u_admin.save()

    p_admin, _ = UserProfile.objects.get_or_create(user=u_admin)
    p_admin.full_name = 'Administrador General Municipal'
    p_admin.rut = '15.234.567-8'
    p_admin.email = 'admin@laserena.cl'
    p_admin.phone = '+56 9 8400 1122'
    p_admin.position = pos_admin
    p_admin.delegation = del_objs["Delegación Centro Histórico"]
    p_admin.status = 'Activo'
    p_admin.deleted_at = None
    p_admin.save()
    p_admin.roles.set([admin_role, super_role])
    print(f"  [USER] admin -> Password: Admin123! (Superuser + Administrador General)")

    # 5. VECINOS DISTRIBUIDOS EN LAS 6 DELEGACIONES (>= 12 en Avenida del Mar para demostrar paginación)
    vecinos_seed = [
        # Avenida del Mar (12 vecinos)
        {"nombre": "Héctor Valenzuela Rojas", "rut": "12.784.561-3", "email": "h.valenzuela@gmail.com", "telefono": "+56 9 5541 2390", "direccion": "Av. Cuatro Esquinas 1205", "territorio": "Delegación Avenida del Mar", "estado": "Activo"},
        {"nombre": "Diego Tapia Castillo", "rut": "19.822.450-3", "email": "diego.tapia@outlook.cl", "telefono": "+56 9 7889 0012", "direccion": "Av. del Mar 4100 Depto 302", "territorio": "Delegación Avenida del Mar", "estado": "Activo"},
        {"nombre": "Camila Andrea Soto", "rut": "17.452.193-4", "email": "camila.soto@gmail.com", "telefono": "+56 9 6654 3210", "direccion": "Los Nísperos 850", "territorio": "Delegación Avenida del Mar", "estado": "Inactivo"},
        {"nombre": "Javiera Paz Olivares", "rut": "16.100.132-K", "email": "javiera.olivares@gmail.com", "telefono": "+56 9 6111 2233", "direccion": "Av. Pacífico 1890", "territorio": "Delegación Avenida del Mar", "estado": "Activo"},
        {"nombre": "Matías Ignacio Galleguillos", "rut": "17.100.140-4", "email": "matias.g@gmail.com", "telefono": "+56 9 6222 3344", "direccion": "Los Arrayanes 430", "territorio": "Delegación Avenida del Mar", "estado": "Activo"},
        {"nombre": "Valentina Constanza Cortés", "rut": "18.100.156-4", "email": "valentina.c@gmail.com", "telefono": "+56 9 6333 4455", "direccion": "Av. del Mar 2950 Depto 501", "territorio": "Delegación Avenida del Mar", "estado": "Activo"},
        {"nombre": "Sebastián Andrés Zepeda", "rut": "19.100.167-3", "email": "sebastian.z@gmail.com", "telefono": "+56 9 6444 5566", "direccion": "Calle Los Lúcumos 610", "territorio": "Delegación Avenida del Mar", "estado": "Activo"},
        {"nombre": "Lorena del Carmen Alfaro", "rut": "20.100.172-2", "email": "lorena.alfaro@gmail.com", "telefono": "+56 9 6555 6677", "direccion": "Pasaje Las Gaviotas 215", "territorio": "Delegación Avenida del Mar", "estado": "Inactivo"},
        {"nombre": "Cristián Eduardo Pizarro", "rut": "21.100.188-2", "email": "cristian.pizarro@gmail.com", "telefono": "+56 9 6666 7788", "direccion": "Av. Cuatro Esquinas 940", "territorio": "Delegación Avenida del Mar", "estado": "Activo"},
        {"nombre": "Paulina Alejandra Carvajal", "rut": "22.100.193-1", "email": "paulina.carvajal@gmail.com", "telefono": "+56 9 6777 8899", "direccion": "Los Perales 775", "territorio": "Delegación Avenida del Mar", "estado": "Activo"},
        {"nombre": "Gonzalo Hernán Santander", "rut": "13.222.111-3", "email": "gonzalo.santander@gmail.com", "telefono": "+56 9 6888 9900", "direccion": "Av. del Mar 3400 Depto 804", "territorio": "Delegación Avenida del Mar", "estado": "Activo"},
        {"nombre": "Claudia Verónica Mundaca", "rut": "14.222.111-0", "email": "claudia.mundaca@gmail.com", "telefono": "+56 9 6999 0011", "direccion": "Calle Los Plátanos 512", "territorio": "Delegación Avenida del Mar", "estado": "Inactivo"},

        # Centro Histórico
        {"nombre": "Rosa Elena Villalobos", "rut": "14.892.314-5", "email": "rosita.villalobos@hotmail.com", "telefono": "+56 9 8471 2033", "direccion": "Calle Balmaceda 1042", "territorio": "Delegación Centro Histórico", "estado": "Activo"},
        {"nombre": "Francisca Godoy Pizarro", "rut": "18.390.412-2", "email": "francisca.godoy@gmail.com", "telefono": "+56 9 9345 6789", "direccion": "Colón 560", "territorio": "Delegación Centro Histórico", "estado": "Activo"},

        # Las Compañías
        {"nombre": "Carlos Morales Pizarro", "rut": "16.241.879-2", "email": "carlos.morales@gmail.com", "telefono": "+56 9 7312 9944", "direccion": "Av. Islón 450", "territorio": "Delegación Las Compañías", "estado": "Activo"},
        {"nombre": "Marcela Damke Marín", "rut": "15.823.119-7", "email": "marcela.damke@yahoo.cl", "telefono": "+56 9 8221 4400", "direccion": "Pasaje El Esfuerzo 102", "territorio": "Delegación Las Compañías", "estado": "Activo"},

        # La Pampa
        {"nombre": "María Ignacia Cortés", "rut": "18.390.412-K", "email": "m.ignacia.cortes@gmail.com", "telefono": "+56 9 9120 4855", "direccion": "Los Corsarios 820", "territorio": "Delegación La Pampa", "estado": "Activo"},
        {"nombre": "Rodrigo Fuenzalida Vásquez", "rut": "13.914.825-1", "email": "rodrigo.fuenzalida@live.cl", "telefono": "+56 9 5122 0651", "direccion": "Larraín Alcalde 3100", "territorio": "Delegación La Pampa", "estado": "Inactivo"},

        # La Antena
        {"nombre": "Patricia Andrea Vega", "rut": "15.632.198-4", "email": "patricia.vega@gmail.com", "telefono": "+56 9 6684 7219", "direccion": "Pasaje Los Naranjos 312", "territorio": "Delegación La Antena", "estado": "Activo"},
        {"nombre": "Carlos Araya Espinoza", "rut": "16.711.205-8", "email": "carlos.araya.e@gmail.com", "telefono": "+56 9 6554 1122", "direccion": "Av. 18 de Septiembre 1450", "territorio": "Delegación La Antena", "estado": "Activo"},

        # Sector Rural
        {"nombre": "Jorge Alberto Cisternas", "rut": "11.450.982-1", "email": "jorge.cisternas@rural.cl", "telefono": "+56 9 4412 9850", "direccion": "Camino San Valentín s/n", "territorio": "Delegación Sector Rural", "estado": "Activo"},
        {"nombre": "Elena Miranda Cortés", "rut": "12.589.633-1", "email": "elena.miranda@gmail.com", "telefono": "+56 9 5543 9988", "direccion": "Quebrada de Talca Parcela 12", "territorio": "Delegación Sector Rural", "estado": "Activo"},
    ]

    for vd in vecinos_seed:
        v, created = Vecino.objects.get_or_create(
            rut=vd["rut"],
            defaults=vd
        )
        if not created:
            for k, val in vd.items():
                setattr(v, k, val)
            v.deleted_at = None
            v.save()
        print(f"  [VECINO] {v.nombre} ({v.rut}) -> {v.territorio} [{v.estado}]")

    # 6. TIPOS DE ATENCIÓN Y SERVICIOS
    att_types = [
        ("TIP-001-ORI", "Orientación Social y Familiar", "Atención social integral DIDECO"),
        ("TIP-002-TER", "Atención Territorial y Comunitaria", "Gestión territorial en juntas de vecinos"),
        ("TIP-003-COM", "Apoyo Comunitario y Emergencia", "Asistencia social ante catástrofes y urgencias"),
        ("TIP-004-SUB", "Subsidios y Beneficios Estatales", "Postulación a subsidios de agua potable y habitacionales"),
        ("TIP-005-MED", "Medio Ambiente y Espacios Verdes", "Requerimientos de podas y áreas verdes"),
        ("TIP-006-SEG", "Seguridad Ciudadana e Iluminación", "Reposición de luminarias y rondas preventivas"),
    ]
    att_map = {}
    for code, name, desc in att_types:
        at, _ = AttentionType.objects.get_or_create(code=code, defaults={"name": name, "description": desc, "status": "Activo"})
        at.name = name
        at.status = "Activo"
        at.deleted_at = None
        at.save()
        att_map[code] = at

    sub_types = [
        ("SUB-001-INF", "Información del Registro Social de Hogares", "TIP-001-ORI"),
        ("SUB-002-CON", "Consulta sobre Espacios Públicos", "TIP-002-TER"),
        ("SUB-003-ORG", "Orientación a Organizaciones Comunitarias", "TIP-003-COM"),
        ("SUB-004-AGU", "Subsidio de Agua Potable (SAP)", "TIP-004-SUB"),
        ("SUB-005-PLA", "Mantención de Áreas Verdes y Podas", "TIP-005-MED"),
        ("SUB-006-LUM", "Reparación de Alumbrado Público", "TIP-006-SEG"),
    ]
    sub_map = {}
    for code, name, parent_code in sub_types:
        parent = att_map[parent_code]
        sub, _ = SubAttention.objects.get_or_create(code=code, defaults={"name": name, "attention_type": parent, "status": "Activo"})
        sub.name = name
        sub.attention_type = parent
        sub.status = "Activo"
        sub.deleted_at = None
        sub.save()
        sub_map[code] = sub

    # 7. PERÍODO OPERATIVO 2026 Y METAS
    period, _ = MeasurementPeriod.objects.get_or_create(
        name="Período Operativo 2026",
        defaults={"start_date": date(2026, 1, 1), "end_date": date(2026, 12, 31), "computable_days": 240, "status": "Abierto"}
    )
    period.status = "Abierto"
    period.computable_days = 240
    period.deleted_at = None
    period.save()

    items = [
        ("ITM-001-ORI", "Orientaciones Sociales Brindadas"),
        ("ITM-002-TER", "Reuniones Territoriales Realizadas"),
        ("ITM-003-COM", "Ayudas Comunitarias Entregadas"),
        ("ITM-004-SUB", "Subsidios y Beneficios Tramitados"),
    ]
    itm_map = {}
    for code, name in items:
        it, _ = MeasurementItem.objects.get_or_create(code=code, defaults={"name": name, "item_type": "Cuantitativo", "status": "Activo"})
        itm_map[code] = it

    goals_data = [
        ("MET-001-ORI", period, pos_asistente, itm_map["ITM-001-ORI"], 40.0, 30.0),
        ("MET-002-TER", period, pos_gestor, itm_map["ITM-002-TER"], 30.0, 25.0),
        ("MET-003-COM", period, pos_delegado, itm_map["ITM-003-COM"], 20.0, 25.0),
        ("MET-004-SUB", period, pos_asistente, itm_map["ITM-004-SUB"], 25.0, 20.0),
    ]
    for code, per, pos, it, target, weight in goals_data:
        g, _ = Goal.objects.get_or_create(code=code, defaults={"period": per, "position": pos, "item": it, "target_value": target, "weight": weight, "unit_of_measure": "Atenciones", "status": "Activo"})
        g.target_value = target
        g.weight = weight
        g.status = "Activo"
        g.save()

    # 8. ATENCIONES CIUDADANAS REALES (PERSISTIDAS EN BD, >= 12 EN AVENIDA DEL MAR PARA PAGINACIÓN)
    atenciones_sample = [
        ("AT-2026-001", "Héctor Valenzuela Rojas", "+56 9 5541 2390", del_objs["Delegación Avenida del Mar"], "TIP-004-SUB", "SUB-004-AGU", "Postulación a Subsidio de Agua Potable (SAP) por vulnerabilidad socioeconómica.", "Ficha social RSH validada al 40%. Ingresado decreto de beneficio.", "Approved"),
        ("AT-2026-002", "Rosa Elena Villalobos", "+56 9 8471 2033", del_objs["Delegación Centro Histórico"], "TIP-001-ORI", "SUB-001-INF", "Actualización de cartola del Registro Social de Hogares.", "Se descarga cartola y se registra cambio de domicilio en el sistema.", "Approved"),
        ("AT-2026-003", "Carlos Morales Pizarro", "+56 9 7312 9944", del_objs["Delegación Las Compañías"], "TIP-002-TER", "SUB-002-CON", "Solicitud de uso de sede comunitaria para junta vecinal.", "Coordinación territorial realizada y espacio reservado.", "Approved"),
        ("AT-2026-004", "Patricia Andrea Vega", "+56 9 6684 7219", del_objs["Delegación La Antena"], "TIP-003-COM", "SUB-003-ORG", "Entrega de canasta de alimentos de emergencia por incendio parcial.", "Se despacharon víveres y materiales con acta de entrega.", "Approved"),
        ("AT-2026-005", "Jorge Alberto Cisternas", "+56 9 4412 9850", del_objs["Delegación Sector Rural"], "TIP-001-ORI", "SUB-001-INF", "Orientación jurídica para renovación de directiva comunitaria rural.", "Se asesoró en asamblea y se remitieron estatutos.", "Pending"),
        ("AT-2026-006", "María Ignacia Cortés", "+56 9 9120 4855", del_objs["Delegación La Pampa"], "TIP-006-SEG", "SUB-006-LUM", "Reporte de falla en luminarias públicas en Los Corsarios.", "Orden de trabajo emitida a cuadrilla de alumbrado público.", "Approved"),
        ("AT-2026-007", "Diego Tapia Castillo", "+56 9 7889 0012", del_objs["Delegación Avenida del Mar"], "TIP-002-TER", "SUB-002-CON", "Visita domiciliaria e inspección en terreno de habitabilidad sociofamiliar.", "Levantamiento fotográfico en terreno y verificación de ficha social.", "Pending"),
        ("AT-2026-008", "Camila Andrea Soto", "+56 9 6654 3210", del_objs["Delegación Avenida del Mar"], "TIP-001-ORI", "SUB-001-INF", "Emisión de informe social oficial para Tribunal de Familia por pensión.", "Informe social pericial emitido formalmente con código INF-2026-AVM-001.", "Approved"),
        ("AT-2026-009", "Javiera Paz Olivares", "+56 9 6111 2233", del_objs["Delegación Avenida del Mar"], "TIP-005-MED", "SUB-005-PLA", "Solicitud de poda preventiva de arbolado urbano frente a acceso peatonal.", "Cuadrilla de áreas verdes programada para intervención en Av. Pacífico.", "Approved"),
        ("AT-2026-010", "Matías Ignacio Galleguillos", "+56 9 6222 3344", del_objs["Delegación Avenida del Mar"], "TIP-006-SEG", "SUB-006-LUM", "Reposición de foco LED en poste de alumbrado público sector Los Arrayanes.", "Derivado a equipo eléctrico municipal para reemplazo de luminaria.", "Pending"),
        ("AT-2026-011", "Valentina Constanza Cortés", "+56 9 6333 4455", del_objs["Delegación Avenida del Mar"], "TIP-004-SUB", "SUB-004-AGU", "Renovación de Subsidio de Agua Potable y actualización de tramo RSH.", "Antecedentes verificados y recepcionados en plataforma DIDECO.", "Approved"),
        ("AT-2026-012", "Sebastián Andrés Zepeda", "+56 9 6444 5566", del_objs["Delegación Avenida del Mar"], "TIP-003-COM", "SUB-003-ORG", "Apoyo social de emergencia por filtración severa de techumbre.", "Evaluación social en terreno y gestión de materiales de emergencia.", "Pending"),
        ("AT-2026-013", "Lorena del Carmen Alfaro", "+56 9 6555 6677", del_objs["Delegación Avenida del Mar"], "TIP-001-ORI", "SUB-001-INF", "Orientación sobre postulación a Subsidio Único Familiar (SUF).", "Se revisa cumplimiento de requisitos y se agenda hora de ingreso.", "Rejected"),
        ("AT-2026-014", "Cristián Eduardo Pizarro", "+56 9 6666 7788", del_objs["Delegación Avenida del Mar"], "TIP-002-TER", "SUB-002-CON", "Coordinación de operativo de limpieza de borde costero con junta vecinal.", "Operativo agendado con Dirección de Aseo y Ornato.", "Approved"),
        ("AT-2026-015", "Paulina Alejandra Carvajal", "+56 9 6777 8899", del_objs["Delegación Avenida del Mar"], "TIP-005-MED", "SUB-005-PLA", "Recuperación de espacio público y mantención de juegos infantiles.", "Inspección técnica realizada por delegación municipal.", "Pending"),
        ("AT-2026-016", "Gonzalo Hernán Santander", "+56 9 6888 9900", del_objs["Delegación Avenida del Mar"], "TIP-006-SEG", "SUB-006-LUM", "Solicitud de patrullaje preventivo nocturno en sector Cuatro Esquinas.", "Requerimiento coordinado con Seguridad Ciudadana Municipal.", "Approved"),
    ]
    for code, contact, phone, deleg, tip_code, sub_code, prob, act_desc, v_status in atenciones_sample:
        v_obj = Vecino.objects.filter(rut__in=[vd['rut'] for vd in vecinos_seed if vd['nombre'] == contact]).first()
        act, created = Activity.objects.get_or_create(
            activity_code=code,
            defaults={
                "contact_name": contact,
                "contact_phone": phone,
                "activity_date": date.today(),
                "delegation": deleg,
                "attention_type": att_map[tip_code],
                "subattention": sub_map[sub_code],
                "problem_description": prob,
                "executed_action": act_desc,
                "validation_status": v_status,
                "neighbor": v_obj,
                "user": u_delegado
            }
        )
        if not created:
            act.contact_name = contact
            act.contact_phone = phone
            act.delegation = deleg
            act.attention_type = att_map[tip_code]
            act.subattention = sub_map[sub_code]
            act.problem_description = prob
            act.executed_action = act_desc
            act.validation_status = v_status
            act.neighbor = v_obj
            act.deleted_at = None
            act.save()
        print(f"  [ATENCIÓN] {act.activity_code} -> {act.contact_name} ({act.delegation.name})")

    # 9. CASOS SOCIALES ÚNICOS (RN-012, >= 10 EN AVENIDA DEL MAR PARA DEMOSTRAR PAGINACIÓN Y 3 ETAPAS)
    casos_seed = [
        ("12.784.561-3", "Héctor Valenzuela Rojas", "+56 9 5541 2390", "[beneficio] Subsidio de Agua Potable (SAP). Adulto mayor con pensión básica solidaria solicita renovación de SAP.", 3),
        ("19.822.450-3", "Diego Tapia Castillo", "+56 9 7889 0012", "[diagnostico] Evaluación habitacional en terreno. Familia monoparental solicita visita domiciliaria por humedad severa.", 2),
        ("17.452.193-4", "Camila Andrea Soto", "+56 9 6654 3210", "[informe] Informe Social para Tribunal de Familia. Requerimiento de peritaje socioeconómico urgente.", 1),
        ("16.100.132-K", "Javiera Paz Olivares", "+56 9 6111 2233", "[beneficio] Canasta Familiar de Alimentos DIDECO. Jefa de hogar cesante requiere apoyo alimentario.", 3),
        ("17.100.140-4", "Matías Ignacio Galleguillos", "+56 9 6222 3344", "[emergencia] Incendio Habitacional parcial. Solicita ayuda de emergencia con colchonetas y frazadas.", 2),
        ("18.100.156-4", "Valentina Constanza Cortés", "+56 9 6333 4455", "[beneficio] Subsidio Único Familiar (SUF). Postulación para dos cargas familiares menores de edad.", 1),
        ("19.100.167-3", "Sebastián Andrés Zepeda", "+56 9 6444 5566", "[redes] Derivación a CESFAM Emilio Schaffhauser. Adulto mayor requiere atención domiciliaria de salud.", 2),
        ("20.100.172-2", "Lorena del Carmen Alfaro", "+56 9 6555 6677", "[beneficio] Exención de Derechos de Aseo Municipal. Vivienda vulnerable tramo 40% RSH.", 3),
        ("21.100.188-2", "Cristián Eduardo Pizarro", "+56 9 6666 7788", "[diagnostico] Visita domiciliaria por hacinamiento. Levantamiento técnico para comité habitacional.", 1),
        ("22.100.193-1", "Paulina Alejandra Carvajal", "+56 9 6777 8899", "[beneficio] Ayuda Médica y Fármacos de alto costo. Receta médica hospitalaria adjunta.", 1),
    ]
    avm_del = del_objs["Delegación Avenida del Mar"]
    for idx, (rut, nombre, fono, problema, max_stage) in enumerate(casos_seed, start=1):
        caso, _ = SocialCase.objects.get_or_create(
            user_rut=rut,
            delegation=avm_del,
            defaults={
                "user_name": nombre,
                "contact_phone": fono,
                "entry_date": date.today(),
            }
        )
        caso.user_name = nombre
        caso.contact_phone = fono
        caso.deleted_at = None
        caso.save()

        m1, _ = SocialManagement.objects.get_or_create(
            case=caso, stage=1,
            defaults={
                "management_type": "Ingreso y recepción de antecedentes",
                "management_date": date.today(),
                "result": problema,
            }
        )
        m1.result = problema
        m1.deleted_at = None
        m1.save()

        if max_stage >= 2:
            m2, _ = SocialManagement.objects.get_or_create(
                case=caso, stage=2,
                defaults={
                    "management_type": "Visita en terreno y levantamiento técnico",
                    "management_date": date.today(),
                    "result": f"[Respaldo: ACT-AVM-0{idx}] Se realizó inspección domiciliaria verificando situación sociofamiliar en terreno.",
                }
            )
            m2.deleted_at = None
            m2.save()
        if max_stage >= 3:
            m3, _ = SocialManagement.objects.get_or_create(
                case=caso, stage=3,
                defaults={
                    "management_type": "Resolución, dictamen y entrega de prestación",
                    "management_date": date.today(),
                    "result": "[Subsidio/Prestación: Beneficio Municipal DIDECO] Caso resuelto favorablemente con acta de entrega.",
                }
            )
            m3.deleted_at = None
            m3.save()
        print(f"  [CASO SOCIAL] #{caso.id} {caso.user_name} ({caso.user_rut}) -> Etapa {max_stage}")

    print("=" * 65)
    print(f"  SEED COMPLETADO CON ÉXITO:")
    print(f"  - Delegaciones: {Delegation.objects.filter(deleted_at__isnull=True).count()}")
    print(f"  - Vecinos en BD: {Vecino.objects.filter(deleted_at__isnull=True).count()}")
    print(f"  - Atenciones en BD: {Activity.objects.filter(deleted_at__isnull=True).count()}")
    print(f"  - Usuarios: {User.objects.count()}")
    print(f"  - Cargos: {Position.objects.filter(deleted_at__isnull=True).count()}")
    print(f"  - Roles: {Role.objects.filter(deleted_at__isnull=True).count()}")
    print("=" * 65)

if __name__ == '__main__':
    seed_pre_evaluation()

