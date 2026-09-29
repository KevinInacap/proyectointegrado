from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from core.models import AuditLog
from organization.models import Delegation, Position, UserProfile
from activities.models import ServiceCatalog, Activity, Evidence, Validation
from metrics.models import MeasurementPeriod, MeasurementItem, Goal, DailyIndicator, PerformanceAdjustment
from agenda.models import CollectiveAgenda, CommitmentHistory
from social.models import SocialCase, SocialManagement


class Command(BaseCommand):
    help = "Carga reproducible de datos maestros, operacionales, auditoría y usuarios de prueba (Evaluación Sumativa II)"

    def handle(self, *args, **options):
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
        # 2. TABLAS MAESTRAS: CARGOS
        # -------------------------------------------------------------
        pos_gestor, _ = Position.objects.get_or_create(
            name="Gestor Territorial",
            defaults={"description": "Atención ciudadana y levantamiento de requerimientos en terreno.", "status": "Activo"}
        )
        pos_verificador, _ = Position.objects.get_or_create(
            name="Verificador de Evidencias",
            defaults={"description": "Revisión y validación formal de evidencias y respaldos fotográficos.", "status": "Activo"}
        )
        pos_director, _ = Position.objects.get_or_create(
            name="Director de Delegación",
            defaults={"description": "Supervisión global de operaciones y cumplimiento de metas.", "status": "Activo"}
        )
        pos_control, _ = Position.objects.get_or_create(
            name="Jefatura de Control y Gestión",
            defaults={"description": "Auditoría institucional y seguimiento de metas comunales.", "status": "Activo"}
        )
        self.stdout.write(self.style.SUCCESS("[OK] Cargos maestros creados."))

        # -------------------------------------------------------------
        # 3. GRUPOS Y PERMISOS DJANGO (ROLES ESTÁNDAR)
        # -------------------------------------------------------------
        # 3.1 Grupo Administradores (Acceso total)
        group_admin, _ = Group.objects.get_or_create(name="Administradores")
        all_permissions = Permission.objects.all()
        group_admin.permissions.set(all_permissions)

        # 3.2 Grupo Verificadores (Revisión y Validación)
        group_verificador, _ = Group.objects.get_or_create(name="Verificadores")
        verif_codenames = [
            'view_activity', 'change_activity',
            'add_validation', 'change_validation', 'view_validation',
            'view_evidence', 'view_servicecatalog',
            'view_delegation', 'view_position', 'view_userprofile',
            'view_measurementperiod', 'view_measurementitem', 'view_goal', 'view_dailyindicator',
            'view_collectiveagenda', 'view_commitmenthistory',
            'view_socialcase', 'view_socialmanagement',
            'view_auditlog'
        ]
        verif_perms = Permission.objects.filter(codename__in=verif_codenames)
        group_verificador.permissions.set(verif_perms)

        # 3.3 Grupo Gestores Territoriales (Operación en terreno - Sin permisos de eliminación física)
        group_gestor, _ = Group.objects.get_or_create(name="Gestores Territoriales")
        gestor_codenames = [
            'add_activity', 'change_activity', 'view_activity',
            'add_evidence', 'change_evidence', 'view_evidence',
            'view_servicecatalog', 'view_delegation',
            'add_collectiveagenda', 'change_collectiveagenda', 'view_collectiveagenda',
            'add_commitmenthistory', 'change_commitmenthistory', 'view_commitmenthistory',
            'add_socialcase', 'change_socialcase', 'view_socialcase',
            'add_socialmanagement', 'change_socialmanagement', 'view_socialmanagement',
            'view_measurementperiod', 'view_goal', 'view_dailyindicator'
        ]
        gestor_perms = Permission.objects.filter(codename__in=gestor_codenames)
        group_gestor.permissions.set(gestor_perms)

        self.stdout.write(self.style.SUCCESS("[OK] Grupos y permisos de Django configurados (Administradores, Verificadores, Gestores Territoriales)."))

        # -------------------------------------------------------------
        # 4. USUARIOS DE PRUEBA Y PERFILES (Múltiples contextos y delegaciones)
        # -------------------------------------------------------------
        def create_test_user(username, email, first_name, last_name, password, group, delegation, position, rut, is_staff=True, is_superuser=False):
            user, _ = User.objects.get_or_create(
                username=username,
                defaults={
                    "email": email,
                    "first_name": first_name,
                    "last_name": last_name,
                    "is_staff": is_staff,
                    "is_superuser": is_superuser,
                }
            )
            user.set_password(password)
            user.is_staff = is_staff
            user.is_superuser = is_superuser
            user.groups.clear()
            user.groups.add(group)
            user.save()

            full_name = f"{first_name} {last_name}"
            profile, _ = UserProfile.objects.get_or_create(
                user=user,
                defaults={
                    "rut": rut,
                    "full_name": full_name,
                    "email": email,
                    "delegation": delegation,
                    "position": position,
                    "status": "Activo"
                }
            )
            profile.rut = rut
            profile.full_name = full_name
            profile.email = email
            profile.delegation = delegation
            profile.position = position
            profile.status = "Activo"
            profile.save()
            return user

        # Administradores
        user_admin = create_test_user(
            "admin", "admin@laserena.cl", "Administrador", "General",
            "Admin1234!", group_admin, del_centro, pos_director, "11.111.111-1",
            is_staff=True, is_superuser=True
        )
        user_control = create_test_user(
            "admin_control", "control@laserena.cl", "Beatriz", "Cisternas Alarcón",
            "Admin1234!", group_admin, del_centro, pos_control, "13.444.555-6",
            is_staff=True, is_superuser=False
        )

        # Verificadores
        user_verificador = create_test_user(
            "verificador", "verificador@laserena.cl", "Esteban", "Morales Vega",
            "Verificador1234!", group_verificador, del_companias, pos_verificador, "15.678.901-2"
        )
        user_verif_centro = create_test_user(
            "verificador_centro", "verif.centro@laserena.cl", "Sofía", "Valenzuela Peña",
            "Verificador1234!", group_verificador, del_centro, pos_verificador, "16.789.012-3"
        )
        user_verif_rural = create_test_user(
            "verificador_rural", "verif.rural@laserena.cl", "Andrea", "Godoy Silva",
            "Verificador1234!", group_verificador, del_rural, pos_verificador, "14.567.890-1"
        )

        # Gestores Territoriales
        user_companias = create_test_user(
            "funcionario_companias", "gestor.companias@laserena.cl", "Rodrigo", "Tapia Gallardo",
            "Funcionario1234!", group_gestor, del_companias, pos_gestor, "17.892.456-3"
        )
        user_centro = create_test_user(
            "funcionario_centro", "gestora.centro@laserena.cl", "Camila", "Araya Miranda",
            "Funcionario1234!", group_gestor, del_centro, pos_gestor, "18.345.678-K"
        )
        user_pampa = create_test_user(
            "funcionario_pampa", "gestor.pampa@laserena.cl", "Kevin", "Encina Molina",
            "Funcionario1234!", group_gestor, del_pampa, pos_gestor, "12.345.678-K"
        )
        user_rural = create_test_user(
            "funcionario_rural", "gestor.rural@laserena.cl", "Manuel", "Barraza Díaz",
            "Funcionario1234!", group_gestor, del_rural, pos_gestor, "19.876.543-2"
        )

        self.stdout.write(self.style.SUCCESS("[OK] 9 Cuentas de prueba creadas y asociadas a Grupos y Delegaciones."))

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
            user_rut="14.223.344-5",
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
            user_rut="16.554.433-2",
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
            " CARGA REPRODUCIBLE DE DATOS COMPLETADA CON ÉXITO \n"
            "=======================================================\n"
            "GRUPOS Y CUENTAS CONFIGURADAS (Django RBAC):\n\n"
            " [GRUPO: Administradores - Acceso Total]\n"
            "  * admin / Admin1234! (RUT: 11.111.111-1) - Centro Histórico [Superuser]\n"
            "  * admin_control / Admin1234! (RUT: 13.444.555-6) - Control Comunal\n\n"
            " [GRUPO: Verificadores - Revisión y Validación]\n"
            "  * verificador / Verificador1234! (RUT: 15.678.901-2) - Las Compañías\n"
            "  * verificador_centro / Verificador1234! (RUT: 16.789.012-3) - Centro Histórico\n"
            "  * verificador_rural / Verificador1234! (RUT: 14.567.890-1) - Sector Rural\n\n"
            " [GRUPO: Gestores Territoriales - Operación y Registro]\n"
            "  * funcionario_companias / Funcionario1234! (RUT: 17.892.456-3) - Las Compañías\n"
            "  * funcionario_centro / Funcionario1234! (RUT: 18.345.678-K) - Centro Histórico\n"
            "  * funcionario_pampa / Funcionario1234! (RUT: 12.345.678-K) - La Pampa\n"
            "  * funcionario_rural / Funcionario1234! (RUT: 19.876.543-2) - Sector Rural\n"
            "======================================================="
        ))
