from datetime import date, timedelta
import os
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User, Group, Permission
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from core.models import AuditLog
from organization.models import Delegation, Position, Role, UserProfile, PermissionDefinition
from organization.access import ADMINISTRATOR_ROLE_NAME, set_role_permission_codes
from organization.views import SYSTEM_PERMISSIONS_CATALOG
from activities.models import ServiceCatalog, Activity, Evidence, Validation
from metrics.models import MeasurementPeriod, MeasurementItem, Goal, DailyIndicator, PerformanceAdjustment
from agenda.models import CollectiveAgenda, CommitmentHistory
from social.models import SocialCase, SocialManagement


class Command(BaseCommand):
    help = "Carga reproducible de datos maestros, operacionales, auditoría y usuarios de prueba (Evaluación Sumativa II)"

    def add_arguments(self, parser):
        parser.add_argument(
            '--include-demo-data',
            action='store_true',
            help='Agrega usuarios y registros ficticios para una demostración local; requiere SGR_SEED_PASSWORD.',
        )

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError('La carga de datos de demostración está bloqueada cuando DEBUG=False.')
        seed_password = os.environ.get('SGR_SEED_PASSWORD', '').strip()
        if options['include_demo_data'] and not seed_password:
            raise CommandError(
                'Para cargar usuarios de prueba define SGR_SEED_PASSWORD en tu entorno local. '
                'No se aceptan cuentas de demostración sin una clave inicial privada.'
            )

        def set_initial_password(user):
            if seed_password:
                user.set_password(seed_password)
            else:
                user.set_unusable_password()

        self.stdout.write(self.style.NOTICE("Iniciando carga reproducible de datos SGR..."))

        # -------------------------------------------------------------
        # 1. TABLAS MAESTRAS: DELEGACIONES
        # -------------------------------------------------------------
        del_companias, _ = Delegation.objects.get_or_create(
            name="Delegación Las Compañías",
            defaults={"scope": "Norte Urbano - Las Compañías", "status": "Activo"}
        )
        del_centro, _ = Delegation.objects.get_or_create(
            name="Delegación Centro Histórico",
            defaults={"scope": "Casco Antiguo y Alrededores", "status": "Activo"}
        )
        del_pampa, _ = Delegation.objects.get_or_create(
            name="Delegación La Pampa",
            defaults={"scope": "Sur Urbano - San Joaquín y La Pampa", "status": "Activo"}
        )
        del_rural, _ = Delegation.objects.get_or_create(
            name="Delegación Rural",
            defaults={"scope": "Valles y Quebradas Interiores", "status": "Activo"}
        )
        self.stdout.write(self.style.SUCCESS("[OK] Delegaciones maestras cargadas."))

        # -------------------------------------------------------------
        # 2. TABLAS MAESTRAS: CARGOS Y ROLES INSTITUCIONALES
        # -------------------------------------------------------------
        pos_admin, _ = Position.objects.get_or_create(
            name="Administrador General",
            defaults={"description": "Administración y seguridad integral del SGR", "status": "Activo"}
        )
        pos_coordinador, _ = Position.objects.get_or_create(
            name="Coordinador del Sistema",
            defaults={"description": "Coordinación operativa y seguimiento comunal.", "status": "Activo"}
        )
        pos_delegado, _ = Position.objects.get_or_create(
            name="Delegado Municipal",
            defaults={"description": "Dirección territorial de una delegación municipal.", "status": "Activo"}
        )
        pos_gestor, _ = Position.objects.get_or_create(
            name="Gestor Territorial",
            defaults={"description": "Gestión de actividades y atención en terreno.", "status": "Activo"}
        )
        pos_asistente_social, _ = Position.objects.get_or_create(
            name="Asistente Social",
            defaults={"description": "Atención social y acompañamiento de casos.", "status": "Activo"}
        )
        pos_verificador, _ = Position.objects.get_or_create(
            name="Verificador Técnico",
            defaults={"description": "Revisión y validación de evidencias.", "status": "Activo"}
        )
        pos_auditor, _ = Position.objects.get_or_create(
            name="Auditor Municipal",
            defaults={"description": "Fiscalización, calidad y auditoría.", "status": "Activo"}
        )

        role_admin, _ = Role.objects.get_or_create(
            name=ADMINISTRATOR_ROLE_NAME,
            defaults={"description": "Configuración integral, parámetros, usuarios y auditoría transversal.", "is_system": True}
        )
        role_admin.is_system = True
        admin_permissions = [
            permission['code']
            for module in SYSTEM_PERMISSIONS_CATALOG
            for permission in module['permissions']
        ]
        for module in SYSTEM_PERMISSIONS_CATALOG:
            for permission in module['permissions']:
                PermissionDefinition.objects.update_or_create(
                    code=permission['code'],
                    defaults={
                        'module_id': module['module_id'],
                        'name': permission['name'],
                        'description': permission['desc'],
                        'is_system': True,
                        'deleted_at': None,
                    },
                )
        set_role_permission_codes(
            role_admin,
            [*admin_permissions, 'lectura', 'edicion', 'derivacion', 'cierre'],
        )
        role_admin.is_system = True
        role_admin.save(update_fields=['is_system', 'updated_at'])
        role_coordinador, _ = Role.objects.get_or_create(
            name="Coordinador del Sistema",
            defaults={"description": "Supervisión institucional, metas y reportes consolidados comunales."}
        )
        role_delegado, _ = Role.objects.get_or_create(
            name="Delegado Municipal",
            defaults={"description": "Jefatura de delegación y gestión del tubo de trabajo colectivo."}
        )
        role_funcionario, _ = Role.objects.get_or_create(
            name="Gestor Territorial",
            defaults={"description": "Registro operativo de actividades, atenciones, compromisos y evidencias."}
        )
        role_verificador, _ = Role.objects.get_or_create(
            name="Verificador Técnico",
            defaults={"description": "Revisión técnica, aprobación o rechazo de evidencias registradas."}
        )
        role_consulta, _ = Role.objects.get_or_create(
            name="Usuario de Consulta",
            defaults={
                "description": "Visualización de tableros, reportes e indicadores sin facultades de edición.",
                "permissions_data": ['lectura'],
            }
        )
        # The application checks these persisted role permissions at request time;
        # Django Groups alone do not authorize its SGR endpoints. Fill only empty
        # system-role matrices so rerunning the seed does not overwrite custom grants.
        role_permission_defaults = (
            (role_coordinador, ['lectura', 'edicion', 'derivacion']),
            (role_delegado, ['lectura', 'edicion', 'derivacion']),
            (role_funcionario, ['lectura', 'edicion', 'derivacion']),
            (role_verificador, ['lectura', 'edicion', 'cierre']),
            (role_consulta, ['lectura']),
        )
        for role, permissions in role_permission_defaults:
            if not role.permissions_data:
                role.permissions_data = permissions
            role.is_system = True
            role.save(update_fields=['permissions_data', 'is_system', 'updated_at'])
        self.stdout.write(self.style.SUCCESS("[OK] Cargos y 6 Roles maestros institucionales creados."))

        # -------------------------------------------------------------
        # 3. GRUPOS Y PERMISOS GRANULARES DJANGO (RBAC MATRIZ SGR)
        # -------------------------------------------------------------
        all_models = [
            AuditLog, Delegation, Position, Role, UserProfile,
            ServiceCatalog, Activity, Evidence, Validation,
            MeasurementPeriod, MeasurementItem, Goal, DailyIndicator, PerformanceAdjustment,
            CollectiveAgenda, CommitmentHistory, SocialCase, SocialManagement
        ]

        def get_model_perms(model, actions=None):
            ct = ContentType.objects.get_for_model(model)
            if actions is None:
                return Permission.objects.filter(content_type=ct)
            codename_suffixes = [f"{action}_{model._meta.model_name}" for action in actions]
            return Permission.objects.filter(content_type=ct, codename__in=codename_suffixes)

        # 3.1 Grupo Administradores (Control total)
        group_admin, _ = Group.objects.get_or_create(name="Administradores")
        for m in all_models:
            group_admin.permissions.add(*get_model_perms(m))

        # 3.2 Grupo Coordinadores (Supervisión transversal y parametrización de metas)
        group_coordinador, _ = Group.objects.get_or_create(name="Coordinadores del Sistema")
        group_coordinador.permissions.clear()
        for m in [MeasurementPeriod, MeasurementItem, Goal, DailyIndicator, PerformanceAdjustment]:
            group_coordinador.permissions.add(*get_model_perms(m))
        for m in [Delegation, Position, Role, UserProfile, ServiceCatalog, Activity, Evidence, Validation, CollectiveAgenda, CommitmentHistory, SocialCase, SocialManagement, AuditLog]:
            group_coordinador.permissions.add(*get_model_perms(m, ['view']))

        # 3.3 Grupo Delegados (Jefatura de delegación y tubo de trabajo)
        group_delegado, _ = Group.objects.get_or_create(name="Delegados Municipales")
        group_delegado.permissions.clear()
        for m in [CollectiveAgenda, CommitmentHistory]:
            group_delegado.permissions.add(*get_model_perms(m, ['view', 'add', 'change']))
        for m in [Activity, Evidence, Validation, DailyIndicator, Goal, MeasurementPeriod, Delegation, UserProfile]:
            group_delegado.permissions.add(*get_model_perms(m, ['view']))

        # 3.4 Grupo Funcionarios Territoriales (Operación en terreno - Sin validación propia)
        group_funcionario, _ = Group.objects.get_or_create(name="Funcionarios Territoriales")
        group_funcionario.permissions.clear()
        for m in [Activity, Evidence, CollectiveAgenda, CommitmentHistory, SocialCase, SocialManagement]:
            group_funcionario.permissions.add(*get_model_perms(m, ['view', 'add', 'change']))
        for m in [ServiceCatalog, MeasurementItem, Goal, DailyIndicator]:
            group_funcionario.permissions.add(*get_model_perms(m, ['view']))

        # 3.5 Grupo Verificadores Técnicos (Validación y auditoría de evidencias)
        group_verificador, _ = Group.objects.get_or_create(name="Verificadores Técnicos")
        group_verificador.permissions.clear()
        group_verificador.permissions.add(*get_model_perms(Validation, ['view', 'add', 'change']))
        for m in [Activity, Evidence, ServiceCatalog, DailyIndicator]:
            group_verificador.permissions.add(*get_model_perms(m, ['view']))

        # 3.6 Grupo Consulta (Solo lectura de indicadores y tableros)
        group_consulta, _ = Group.objects.get_or_create(name="Usuarios de Consulta")
        group_consulta.permissions.clear()
        for m in [Activity, DailyIndicator, Goal, MeasurementPeriod, ServiceCatalog, CollectiveAgenda]:
            group_consulta.permissions.add(*get_model_perms(m, ['view']))

        self.stdout.write(self.style.SUCCESS("[OK] 6 Grupos y permisos granulares de Django configurados (RBAC institucional)."))

        if not options['include_demo_data']:
            self.stdout.write(self.style.SUCCESS(
                'Carga de catálogos completada: delegaciones, cargos, roles y permisos quedaron intactos. '
                'No se agregaron usuarios ni datos operativos ficticios. '
                'Los registros existentes no se eliminan ni modifican.'
            ))
            return

        # -------------------------------------------------------------
        # 4. USUARIOS DE PRUEBA Y PERFILES (Matriz SGR Completa)
        # -------------------------------------------------------------
        # 4.1 Administrador Global
        user_admin, created = User.objects.get_or_create(
            username="admin",
            defaults={
                "email": "admin@example.invalid",
                "first_name": "Demo",
                "last_name": "Administrador",
                "is_staff": False,
                "is_superuser": False,
            }
        )
        if created:
            set_initial_password(user_admin)
        user_admin.groups.add(group_admin)
        user_admin.save()
        profile_admin, _ = UserProfile.objects.get_or_create(
            user=user_admin,
            defaults={
                "rut": "00.000.001-0",
                "full_name": "Usuario Demo Administrador",
                "email": "admin@example.invalid",
                "delegation": del_centro,
                "position": pos_admin,
                "status": "Activo"
            }
        )
        profile_admin.roles.add(role_admin)

        # 4.2 Coordinador del Sistema
        user_coordinador, created = User.objects.get_or_create(
            username="coordinador",
            defaults={
                "email": "coordinador@example.invalid",
                "first_name": "Demo",
                "last_name": "Coordinador",
                "is_staff": True,
                "is_superuser": False,
            }
        )
        if created:
            set_initial_password(user_coordinador)
        user_coordinador.groups.add(group_coordinador)
        user_coordinador.save()
        profile_coord, _ = UserProfile.objects.get_or_create(
            user=user_coordinador,
            defaults={
                "rut": "00.000.002-0",
                "full_name": "Usuario Demo Coordinador",
                "email": "coordinador@example.invalid",
                "delegation": del_centro,
                "position": pos_coordinador,
                "status": "Activo"
            }
        )
        profile_coord.roles.add(role_coordinador)

        # 4.3 Delegado Municipal (Jefatura Las Compañías)
        user_delegado, created = User.objects.get_or_create(
            username="delegado_companias",
            defaults={
                "email": "delegado@example.invalid",
                "first_name": "Demo",
                "last_name": "Delegado",
                "is_staff": True,
                "is_superuser": False,
            }
        )
        if created:
            set_initial_password(user_delegado)
        user_delegado.groups.add(group_delegado)
        user_delegado.save()
        profile_delegado, _ = UserProfile.objects.get_or_create(
            user=user_delegado,
            defaults={
                "rut": "00.000.003-0",
                "full_name": "Usuario Demo Delegado",
                "email": "delegado@example.invalid",
                "delegation": del_companias,
                "position": pos_delegado,
                "status": "Activo"
            }
        )
        profile_delegado.roles.add(role_delegado)

        # 4.4 Funcionario Territorial 1 (Contexto: Delegación Las Compañías)
        user_companias, created = User.objects.get_or_create(
            username="funcionario_companias",
            defaults={
                "email": "funcionario1@example.invalid",
                "first_name": "Demo",
                "last_name": "Funcionario 1",
                "is_staff": True,
                "is_superuser": False,
            }
        )
        if created:
            set_initial_password(user_companias)
        user_companias.groups.add(group_funcionario)
        user_companias.save()
        profile_companias, _ = UserProfile.objects.get_or_create(
            user=user_companias,
            defaults={
                "rut": "00.000.004-0",
                "full_name": "Usuario Demo Funcionario 1",
                "email": "funcionario1@example.invalid",
                "delegation": del_companias,
                "position": pos_gestor,
                "status": "Activo"
            }
        )
        profile_companias.roles.add(role_funcionario)

        # 4.5 Funcionario Territorial 2 (Contexto: Delegación Centro Histórico)
        user_centro, created = User.objects.get_or_create(
            username="funcionario_centro",
            defaults={
                "email": "funcionario2@example.invalid",
                "first_name": "Demo",
                "last_name": "Funcionario 2",
                "is_staff": True,
                "is_superuser": False,
            }
        )
        if created:
            set_initial_password(user_centro)
        user_centro.groups.add(group_funcionario)
        user_centro.save()
        profile_centro, _ = UserProfile.objects.get_or_create(
            user=user_centro,
            defaults={
                "rut": "00.000.005-0",
                "full_name": "Usuario Demo Funcionario 2",
                "email": "funcionario2@example.invalid",
                "delegation": del_centro,
                "position": pos_gestor,
                "status": "Activo"
            }
        )
        profile_centro.roles.add(role_funcionario)

        # 4.6 Verificador Municipal
        user_verificador, created = User.objects.get_or_create(
            username="verificador",
            defaults={
                "email": "verificador@example.invalid",
                "first_name": "Demo",
                "last_name": "Verificador",
                "is_staff": True,
                "is_superuser": False,
            }
        )
        if created:
            set_initial_password(user_verificador)
        user_verificador.groups.add(group_verificador)
        user_verificador.save()
        profile_verificador, _ = UserProfile.objects.get_or_create(
            user=user_verificador,
            defaults={
                "rut": "00.000.006-0",
                "full_name": "Usuario Demo Verificador",
                "email": "verificador@example.invalid",
                "delegation": del_companias,
                "position": pos_verificador,
                "status": "Activo"
            }
        )
        profile_verificador.roles.add(role_verificador)

        # 4.7 Usuario de Consulta / Auditoría
        user_consulta, created = User.objects.get_or_create(
            username="consulta",
            defaults={
                "email": "consulta@example.invalid",
                "first_name": "Demo",
                "last_name": "Consulta",
                "is_staff": True,
                "is_superuser": False,
            }
        )
        if created:
            set_initial_password(user_consulta)
        user_consulta.groups.add(group_consulta)
        user_consulta.save()
        profile_consulta, _ = UserProfile.objects.get_or_create(
            user=user_consulta,
            defaults={
                "rut": "00.000.007-0",
                "full_name": "Usuario Demo Consulta",
                "email": "consulta@example.invalid",
                "delegation": del_centro,
                "position": pos_auditor,
                "status": "Activo"
            }
        )
        profile_consulta.roles.add(role_consulta)

        self.stdout.write(self.style.SUCCESS("[OK] Cuentas y perfiles creados para todos los roles (admin, coordinador, delegado, gestores, verificador, consulta)."))

        # -------------------------------------------------------------
        # 5. TABLAS MAESTRAS: CATÁLOGO DE SERVICIOS
        # -------------------------------------------------------------
        cat_agua, _ = ServiceCatalog.objects.get_or_create(
            service="Subsidio de Agua Potable y Alcantarillado (SAP)",
            attention_type="Postulación presencial y orientación",
            defaults={"area": "Social", "subattention_type": "Renovación subsidio", "status": "Activo"}
        )
        cat_fibe, _ = ServiceCatalog.objects.get_or_create(
            service="Ficha Básica de Emergencia (FIBE)",
            attention_type="Encuesta y catastro en terreno",
            defaults={"area": "Social", "subattention_type": "Afectación por temporal", "status": "Activo"}
        )
        cat_tolva, _ = ServiceCatalog.objects.get_or_create(
            service="Operativo de Tolva y Despeje de Microbasurales",
            attention_type="Coordinación operativa territorial",
            defaults={"area": "Operativo", "subattention_type": "Retiro de voluminosos", "status": "Activo"}
        )
        cat_alumbrado, _ = ServiceCatalog.objects.get_or_create(
            service="Inspección y Reparación de Luminarias",
            attention_type="Requerimiento vecinal de seguridad",
            defaults={"area": "Operativo", "subattention_type": "Alumbrado público", "status": "Activo"}
        )
        cat_vecinos, _ = ServiceCatalog.objects.get_or_create(
            service="Asesoría Jurídica y Social a Organizaciones Comunitarias",
            attention_type="Audiencia en terreno",
            defaults={"area": "Comunitario", "subattention_type": "Renovación directiva", "status": "Activo"}
        )
        self.stdout.write(self.style.SUCCESS("[OK] Catálogo de Servicios institucional configurado."))

        # -------------------------------------------------------------
        # 6. TABLAS MAESTRAS: PERÍODOS E ÍTEMS DE MEDICIÓN
        # -------------------------------------------------------------
        periodo_actual, _ = MeasurementPeriod.objects.get_or_create(
            name="Primer Semestre 2026",
            defaults={
                "start_date": date(2026, 1, 1),
                "end_date": date(2026, 6, 30),
                "computable_days": 120,
                "minimum_threshold": 80.00,
                "compliance_cap": 150.00,
                "status": "Abierto"
            }
        )
        periodo_sgte, _ = MeasurementPeriod.objects.get_or_create(
            name="Segundo Semestre 2026",
            defaults={
                "start_date": date(2026, 7, 1),
                "end_date": date(2026, 12, 31),
                "computable_days": 120,
                "minimum_threshold": 80.00,
                "compliance_cap": 150.00,
                "status": "Planificado"
            }
        )

        item_atenciones, _ = MeasurementItem.objects.get_or_create(
            name="Atenciones Sociales Efectivas en Terreno",
            defaults={"description": "Total de atenciones vecinales con ficha y seguimiento.", "item_type": "Cuantitativo", "status": "Activo"}
        )
        item_operativos, _ = MeasurementItem.objects.get_or_create(
            name="Operativos de Despeje y Espacio Público",
            defaults={"description": "Operativos territoriales concluidos.", "item_type": "Cuantitativo", "status": "Activo"}
        )
        item_resolucion, _ = MeasurementItem.objects.get_or_create(
            name="Tasa de Cierre de Requerimientos Vecinales",
            defaults={"description": "Porcentaje de compromisos cumplidos en plazo.", "item_type": "Porcentual", "status": "Activo"}
        )

        Goal.objects.get_or_create(
            period=periodo_actual,
            position=pos_gestor,
            item=item_atenciones,
            defaults={"target_value": 150.00, "unit_of_measure": "Atenciones", "weight": 50.00}
        )
        Goal.objects.get_or_create(
            period=periodo_actual,
            position=pos_gestor,
            item=item_operativos,
            defaults={"target_value": 24.00, "unit_of_measure": "Operativos", "weight": 50.00}
        )
        self.stdout.write(self.style.SUCCESS("[OK] Períodos, Ítems y Metas de Gestión registrados."))

        # -------------------------------------------------------------
        # 7. TABLAS OPERATIVAS: ACTIVIDADES Y EVIDENCIAS (Contextos 1 y 2)
        # -------------------------------------------------------------
        # 7.1 Actividades de Las Compañías (Rodrigo Tapia)
        act1, _ = Activity.objects.get_or_create(
            activity_code="ACT-2026-COMP-001",
            defaults={
                "user": user_companias,
                "delegation": del_companias,
                "period": periodo_actual,
                "item": item_operativos,
                "catalog": cat_tolva,
                "activity_date": date(2026, 3, 10),
                "problem_description": "Microbasural clandestino en intersección calle Esmeralda con Viña del Mar.",
                "executed_action": "Coordinación de tolva comunal y retiro de 4 toneladas de escombros con cuadrilla territorial.",
                "contact_name": "Manuel Olivares (JJVV Villa Los Jazmines)",
                "contact_phone": "+56987654321",
                "is_collective_agenda": True,
                "validation_status": "Approved",
            }
        )
        Evidence.objects.get_or_create(
            activity=act1,
            evidence_code="EVI-COMP-001-A",
            defaults={
                "file_name": "registro_tolva_esmeralda_antes.jpg",
                "file_path": "/evidencias/2026/companias/tolva_antes.jpg",
                "uploaded_by": user_companias
            }
        )
        Evidence.objects.get_or_create(
            activity=act1,
            evidence_code="EVI-COMP-001-B",
            defaults={
                "file_name": "acta_entrega_terreno_limpio.pdf",
                "file_path": "/evidencias/2026/companias/acta_limpieza.pdf",
                "uploaded_by": user_companias
            }
        )
        Validation.objects.get_or_create(
            activity=act1,
            verifier=user_verificador,
            defaults={
                "decision": "Approved",
                "observations": "Evidencias fotográficas y acta de entrega conformes a protocolo técnico."
            }
        )

        act2, _ = Activity.objects.get_or_create(
            activity_code="ACT-2026-COMP-002",
            defaults={
                "user": user_companias,
                "delegation": del_companias,
                "period": periodo_actual,
                "item": item_atenciones,
                "catalog": cat_agua,
                "activity_date": date(2026, 3, 18),
                "problem_description": "Familia de adulto mayor en situación de vulnerabilidad requiere subsidio de agua potable.",
                "executed_action": "Ingreso presencial de postulación y revisión de cartola RSH.",
                "contact_name": "Rosa Pizarro",
                "contact_phone": "+56976543210",
                "is_collective_agenda": False,
                "validation_status": "Pending",
            }
        )

        # 7.2 Actividad con Soft Delete en Las Compañías (Auditoría: deleted_at registrado)
        act3_deleted, _ = Activity.objects.get_or_create(
            activity_code="ACT-2026-COMP-003-DEL",
            defaults={
                "user": user_companias,
                "delegation": del_companias,
                "period": periodo_actual,
                "item": item_operativos,
                "catalog": cat_alumbrado,
                "activity_date": date(2026, 2, 20),
                "problem_description": "Falla de luminaria en Pasaje San Pedro (registro duplicado por error de digitación).",
                "executed_action": "Registro duplicado enviado a papelera por gestor municipal.",
                "contact_name": "Vecino Juan Pérez",
                "contact_phone": "+56911223344",
                "is_collective_agenda": False,
                "validation_status": "Rejected",
                "deleted_at": timezone.now() - timedelta(days=2),
            }
        )

        # 7.3 Actividades de Centro Histórico (Camila Araya)
        act4, _ = Activity.objects.get_or_create(
            activity_code="ACT-2026-CENT-001",
            defaults={
                "user": user_centro,
                "delegation": del_centro,
                "period": periodo_actual,
                "item": item_atenciones,
                "catalog": cat_vecinos,
                "activity_date": date(2026, 3, 12),
                "problem_description": "Reunión extraordinaria con directiva JJVV Centro La Serena sobre recuperación de fachada patrimonial.",
                "executed_action": "Mesa de trabajo y redacción de compromiso territorial con Dirección de Obras.",
                "contact_name": "Ignacio Valenzuela",
                "contact_phone": "+56965432109",
                "is_collective_agenda": True,
                "validation_status": "Approved",
            }
        )
        Evidence.objects.get_or_create(
            activity=act4,
            evidence_code="EVI-CENT-001-A",
            defaults={
                "file_name": "asistencia_reunion_centro.pdf",
                "file_path": "/evidencias/2026/centro/asistencia_centro.pdf",
                "uploaded_by": user_centro
            }
        )

        act5, _ = Activity.objects.get_or_create(
            activity_code="ACT-2026-CENT-002",
            defaults={
                "user": user_centro,
                "delegation": del_centro,
                "period": periodo_actual,
                "item": item_operativos,
                "catalog": cat_alumbrado,
                "activity_date": date(2026, 3, 22),
                "problem_description": "Luminaria apagada en calle Balmaceda con Cordovez afectando seguridad peatonal.",
                "executed_action": "Inspección técnica y notificación prioritaria a empresa de mantenimiento eléctrico.",
                "contact_name": "Comerciante Patricia Soto",
                "contact_phone": "+56954321098",
                "is_collective_agenda": False,
                "validation_status": "Pending",
            }
        )
        self.stdout.write(self.style.SUCCESS("[OK] Actividades, Evidencias y Validaciones cargadas en ambos contextos."))

        # -------------------------------------------------------------
        # 8. TABLAS OPERATIVAS: AGENDA COLECTIVA (Compromisos y Trazabilidad)
        # -------------------------------------------------------------
        compr1, _ = CollectiveAgenda.objects.get_or_create(
            requester="JJVV Villa Los Jazmines",
            territory="Las Compañías Alta",
            defaults={
                "source_activity": act1,
                "delegation": del_companias,
                "assigned_to": user_companias,
                "request_source": "Externo",
                "support_area": "Medio Ambiente y Operaciones",
                "description": "Segunda fecha de operativo de tolva y arborización de plaza pública comunitaria.",
                "committed_date": date(2026, 4, 15),
                "status": "En proceso",
                "observations": "Coordinación confirmada con Dirección de Medio Ambiente."
            }
        )
        CommitmentHistory.objects.get_or_create(
            commitment=compr1,
            previous_status="Ingresado",
            new_status="En proceso",
            defaults={
                "author": user_companias,
                "observations": "Se aprueba fecha de terreno con junta de vecinos."
            }
        )

        compr2, _ = CollectiveAgenda.objects.get_or_create(
            requester="Cámara de Comercio Centro La Serena",
            territory="Casco Histórico",
            defaults={
                "source_activity": act4,
                "delegation": del_centro,
                "assigned_to": user_centro,
                "request_source": "Externo",
                "support_area": "Seguridad Ciudadana",
                "description": "Rondas de patrullaje preventivo nocturno en sector céntrico.",
                "committed_date": date(2026, 4, 2),
                "status": "Pendiente",
                "observations": "En espera de confirmación de inspectores municipales."
            }
        )
        self.stdout.write(self.style.SUCCESS("[OK] Agenda Colectiva e Historial de Compromisos registrados."))

        # -------------------------------------------------------------
        # 9. TABLAS OPERATIVAS: CASOS SOCIALES Y GESTIONES (RN-012)
        # -------------------------------------------------------------
        # Caso Social en Las Compañías
        caso1, _ = SocialCase.objects.get_or_create(
            user_rut="00.000.101-0",
            defaults={
                "user_name": "Elena Morales Castro",
                "contact_phone": "+56944332211",
                "delegation": del_companias,
                "entry_date": date(2026, 2, 10),
            }
        )
        SocialManagement.objects.get_or_create(
            case=caso1,
            stage=1,
            defaults={
                "catalog": cat_agua,
                "management_type": "Recepción y evaluación de antecedentes socioeconómicos",
                "management_date": date(2026, 2, 12),
                "result": "Documentación completa. Derivado a verificación de registro social de hogares."
            }
        )
        SocialManagement.objects.get_or_create(
            case=caso1,
            stage=2,
            defaults={
                "catalog": cat_agua,
                "management_type": "Ingreso a plataforma ministerial de subsidios",
                "management_date": date(2026, 2, 28),
                "result": "Postulación aceptada con 100% de subsidio de consumo básico."
            }
        )

        # Caso Social en Centro Histórico
        caso2, _ = SocialCase.objects.get_or_create(
            user_rut="00.000.102-0",
            defaults={
                "user_name": "Jorge Benítez Rojas",
                "contact_phone": "+56933221100",
                "delegation": del_centro,
                "entry_date": date(2026, 3, 5),
            }
        )
        SocialManagement.objects.get_or_create(
            case=caso2,
            stage=1,
            defaults={
                "catalog": cat_fibe,
                "management_type": "Aplicación de ficha básica por daño en techumbre",
                "management_date": date(2026, 3, 6),
                "result": "Ficha FIBE aplicada y derivada al departamento social central."
            }
        )
        self.stdout.write(self.style.SUCCESS("[OK] Casos Sociales y Gestiones encadenadas creadas."))

        # -------------------------------------------------------------
        # 10. AUDITORIA TRANSVERSAL (RNF-008)
        # -------------------------------------------------------------
        AuditLog.objects.get_or_create(
            affected_table="actividad",
            affected_record_id=str(act1.id),
            action="CREATE",
            defaults={
                "user": user_companias,
                "source_ip": "192.168.1.45",
                "new_value": {"code": act1.activity_code, "status": act1.validation_status}
            }
        )
        AuditLog.objects.get_or_create(
            affected_table="actividad",
            affected_record_id=str(act1.id),
            action="VALIDATE",
            defaults={
                "user": user_verificador,
                "source_ip": "192.168.1.10",
                "new_value": {"decision": "Approved"}
            }
        )
        AuditLog.objects.get_or_create(
            affected_table="actividad",
            affected_record_id=str(act3_deleted.id),
            action="DELETE",
            defaults={
                "user": user_companias,
                "source_ip": "192.168.1.45",
                "previous_value": {"deleted_at": str(act3_deleted.deleted_at)}
            }
        )
        self.stdout.write(self.style.SUCCESS("[OK] Registros de Auditoria transversal creados."))

        self.stdout.write(self.style.SUCCESS(
            "\n=======================================================\n"
            " CARGA REPRODUCIBLE DE DATOS COMPLETADA CON EXITO \n"
            "=======================================================\n"
            "Cuentas de prueba disponibles solo en desarrollo.\n"
            "Las claves existentes no se modificaron; rota las claves iniciales antes de compartir el entorno.\n"
            "======================================================="
        ))
