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
from organization.access import ADMINISTRATOR_ROLE_NAME, SUPER_ADMINISTRATOR_ROLE_NAME

User = get_user_model()

def seed_pre_evaluation():
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
            'is_system': False,
            'permissions_data': ['lectura', 'edicion', 'derivacion', 'cierre']
        }
    )
    asistente_role.permissions_data = ['lectura', 'edicion', 'derivacion', 'cierre']
    asistente_role.save()

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

    # 3. CARGOS MUNICIPALES (DESCRIPTOR DE FUNCIONES 2026 - DECRETO N° 3096)
    pos_asistente, _ = Position.objects.get_or_create(name="Asistente Social", defaults={"description": "Gestor Social: Atención de Casos (Eje I), Acciones Comunitarias OOCC (Eje II), Coordinación/Recursos (Eje III) y Auto-mejora (Eje IV)", "status": "Activo"})
    pos_admin, _ = Position.objects.get_or_create(name="Administrador General", defaults={"description": "Coordinación y gestión de la plataforma SGR", "status": "Activo"})
    pos_super, _ = Position.objects.get_or_create(name="SuperAdministrador", defaults={"description": "Dirección superior y gobernanza SGR", "status": "Activo"})
    pos_gestor, _ = Position.objects.get_or_create(name="Gestor Territorial", defaults={"description": "Gestión vecinal y comunitaria en terreno", "status": "Activo"})
    pos_delegado, _ = Position.objects.get_or_create(name="Delegado Municipal", defaults={"description": "Representante directo de Alcaldía en el territorio; Semáforo SGR, felicitaciones formales, ausencias y liderazgo de equipo", "status": "Activo"})
    pos_apoyo_adm, _ = Position.objects.get_or_create(name="Apoyo Administrativo", defaults={"description": "Agenda del Delegado, transporte, mantención/auxiliares, registro SGR con llamado preventivo, inventario trimestral e informes de personal/transparencia", "status": "Activo"})
    pos_oocc, _ = Position.objects.get_or_create(name="Organizaciones Comunitarias", defaults={"description": "Constitución y vigencia OOCC Leyes 19.418 y 20.500, 5 subfamilias funcionales/territoriales, verificación base JJVV y talleres", "status": "Activo"})
    pos_compras, _ = Position.objects.get_or_create(name="Gestor de Compras y Proyectos", defaults={"description": "Titular/Suplente Decreto Alcaldicio: POA, Control PAC, V°B° pliegos Unidad Revisora, Oficios de Contratación y propuesta ITC", "status": "Activo"})
    pos_planificacion, _ = Position.objects.get_or_create(name="Gestión y Planificación", defaults={"description": "Diagnóstico estratégico del sector, auditoría Matriz SGR por colaborador (fortalezas/debilidades), derivaciones de Gabinete y reunión semanal", "status": "Activo"})
    pos_servicios, _ = Position.objects.get_or_create(name="Coordinador de Servicios Comunitarios", defaults={"description": "Operativos de limpieza y recuperación BNUP, cuadrillas de empleabilidad y emergencia polifuncional, educación ambiental y denuncias de espacios públicos", "status": "Activo"})

    for p in (pos_asistente, pos_admin, pos_super, pos_gestor, pos_delegado, pos_apoyo_adm, pos_oocc, pos_compras, pos_planificacion, pos_servicios):
        p.status = 'Activo'
        p.deleted_at = None
        p.save()

    # 4. CUENTAS DE USUARIO CLAVE PARA LA EVALUACIÓN Y LOS 7 PERFILES DEL DESCRIPTOR 2026
    # 4.1 Scarlett Williams (Asistente Social / Gestor Social + Rol Administrador)
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
    p_scarlett.roles.set([admin_role, asistente_role])
    print(f"  [USER] scarlett -> Password: Admin123! (Gestor Social / Asistente Social)")

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

    # 4.3 Los demás perfiles oficiales del Descriptor de Funciones 2026
    perfiles_2026_users = [
        ('delegado', 'Javier Ignacio', 'Godoy Cazaux', '14.521.309-4', 'javier.godoy@laserena.cl', '+56 9 8112 3344', pos_delegado, "Delegación Avenida del Mar"),
        ('administrativo', 'Marcela Paz', 'Zepeda Rojas', '16.410.228-7', 'marcela.zepeda@laserena.cl', '+56 9 8223 4455', pos_apoyo_adm, "Delegación Avenida del Mar"),
        ('oocc', 'Rodrigo Andrés', 'Pizarro Santander', '17.309.114-K', 'rodrigo.pizarro@laserena.cl', '+56 9 8334 5566', pos_oocc, "Delegación Las Compañías"),
        ('compras', 'Claudia Alejandra', 'Araya Contreras', '15.908.431-2', 'claudia.araya@laserena.cl', '+56 9 8445 6677', pos_compras, "Delegación La Pampa"),
        ('planificacion', 'Camila Fernanda', 'Cortés Alcayaga', '18.112.540-6', 'camila.cortes@laserena.cl', '+56 9 8556 7788', pos_planificacion, "Delegación Centro Histórico"),
        ('servicios', 'Héctor Mauricio', 'Olivares Galleguillos', '13.785.920-1', 'hector.olivares@laserena.cl', '+56 9 8667 8899', pos_servicios, "Delegación La Antena"),
    ]
    for uname, fname, lname, rut, email, phone, pos_obj, del_name in perfiles_2026_users:
        u_obj, _ = User.objects.get_or_create(username=uname)
        u_obj.set_password('Admin123!')
        u_obj.first_name = fname
        u_obj.last_name = lname
        u_obj.email = email
        u_obj.is_active = True
        u_obj.save()

        role_obj, _ = Role.objects.get_or_create(
            name=pos_obj.name,
            defaults={
                'description': pos_obj.description,
                'is_system': False,
                'permissions_data': ['lectura', 'edicion', 'derivacion', 'cierre'],
            },
        )
        role_obj.permissions_data = ['lectura', 'edicion', 'derivacion', 'cierre']
        role_obj.save()

        prof_obj, _ = UserProfile.objects.get_or_create(user=u_obj)
        prof_obj.full_name = f"{fname} {lname}"
        prof_obj.rut = rut
        prof_obj.email = email
        prof_obj.phone = phone
        prof_obj.position = pos_obj
        prof_obj.delegation = del_objs[del_name]
        prof_obj.status = 'Activo'
        prof_obj.deleted_at = None
        prof_obj.save()
        prof_obj.roles.set([role_obj])
        print(f"  [USER] {uname} -> Password: Admin123! ({pos_obj.name} - {del_name})")

    # 5. VECINOS DISTRIBUIDOS EN LAS 6 DELEGACIONES (>= 2 por sede, total 14 vecinos)
    vecinos_seed = [
        # Avenida del Mar
        {"nombre": "Héctor Valenzuela Rojas", "rut": "12.784.561-3", "email": "h.valenzuela@gmail.com", "telefono": "+56 9 5541 2390", "direccion": "Av. Cuatro Esquinas 1205", "territorio": "Delegación Avenida del Mar", "estado": "Activo"},
        {"nombre": "Diego Tapia Castillo", "rut": "19.822.450-3", "email": "diego.tapia@outlook.cl", "telefono": "+56 9 7889 0012", "direccion": "Av. del Mar 4100 Depto 302", "territorio": "Delegación Avenida del Mar", "estado": "Activo"},
        {"nombre": "Camila Andrea Soto", "rut": "17.452.193-4", "email": "camila.soto@gmail.com", "telefono": "+56 9 6654 3210", "direccion": "Los Nísperos 850", "territorio": "Delegación Avenida del Mar", "estado": "Inactivo"},

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
        defaults={"start_date": date(2026, 1, 1), "end_date": date(2026, 12, 31), "status": "Activo"}
    )
    period.status = "Activo"
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

    # 8. ATENCIONES CIUDADANAS REALES (PERSISTIDAS EN BD)
    atenciones_sample = [
        ("AT-2026-001", "Héctor Valenzuela Rojas", "+56 9 5541 2390", del_objs["Delegación Avenida del Mar"], "TIP-004-SUB", "SUB-004-AGU", "Postulación a Subsidio de Agua Potable (SAP) por vulnerabilidad socioeconómica.", "Ficha social RSH validada al 40%. Ingresado decreto de beneficio.", "Approved"),
        ("AT-2026-002", "Rosa Elena Villalobos", "+56 9 8471 2033", del_objs["Delegación Centro Histórico"], "TIP-001-ORI", "SUB-001-INF", "Actualización de cartola del Registro Social de Hogares.", "Se descarga cartola y se registra cambio de domicilio en el sistema.", "Approved"),
        ("AT-2026-003", "Carlos Morales Pizarro", "+56 9 7312 9944", del_objs["Delegación Las Compañías"], "TIP-002-TER", "SUB-002-CON", "Solicitud de uso de sede comunitaria para junta vecinal.", "Coordinación territorial realizada y espacio reservado.", "Approved"),
        ("AT-2026-004", "Patricia Andrea Vega", "+56 9 6684 7219", del_objs["Delegación La Antena"], "TIP-003-COM", "SUB-003-ORG", "Entrega de canasta de alimentos de emergencia por incendio parcial.", "Se despacharon víveres y materiales con acta de entrega.", "Approved"),
        ("AT-2026-005", "Jorge Alberto Cisternas", "+56 9 4412 9850", del_objs["Delegación Sector Rural"], "TIP-001-ORI", "SUB-001-INF", "Orientación jurídica para renovación de directiva comunitaria rural.", "Se asesoró en asamblea y se remitieron estatutos.", "Pending"),
        ("AT-2026-006", "María Ignacia Cortés", "+56 9 9120 4855", del_objs["Delegación La Pampa"], "TIP-006-SEG", "SUB-006-LUM", "Reporte de falla en luminarias públicas en Los Corsarios.", "Orden de trabajo emitida a cuadrilla de alumbrado público.", "Approved"),
        ("AT-2026-007", "Diego Tapia Castillo", "+56 9 7889 0012", del_objs["Delegación Avenida del Mar"], "TIP-002-TER", "SUB-002-CON", "Visita domiciliaria e inspección en terreno de habitabilidad sociofamiliar.", "Levantamiento fotográfico en terreno y verificación de ficha social.", "Pending"),
        ("AT-2026-008", "Camila Andrea Soto", "+56 9 6654 3210", del_objs["Delegación Avenida del Mar"], "TIP-001-ORI", "SUB-001-INF", "Emisión de informe social oficial para Tribunal de Familia por pensión.", "Informe social pericial emitido formalmente con código INF-2026-AVM-001.", "Approved"),
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
                "user": u_scarlett
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
