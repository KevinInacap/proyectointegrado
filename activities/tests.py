from datetime import date, timedelta
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User, Group
from organization.models import Delegation, Position, UserProfile
from activities.models import ServiceCatalog, Activity, Evidence, Validation


class ActivityModelTests(TestCase):
    """
    Pruebas unitarias de modelos, validaciones y auditoría (Evaluación Sumativa II).
    """
    def setUp(self):
        # 1. Crear Delegaciones
        self.del_companias = Delegation.objects.create(name="Delegación Las Compañías", scope="Norte Urbano")
        self.del_centro = Delegation.objects.create(name="Delegación Centro Histórico", scope="Casco Antiguo")

        # 2. Crear Grupos
        self.group_admin = Group.objects.create(name="Administradores")
        self.group_gestores = Group.objects.create(name="Gestores Territoriales")

        # 3. Crear Usuarios de prueba (Contexto 1 y Contexto 2)
        self.user_admin = User.objects.create_superuser(username="admin_test", email="admin@test.cl", password="Password123!")
        self.user_admin.groups.add(self.group_admin)

        self.user_gestor = User.objects.create_user(username="gestor_companias", email="gestor@test.cl", password="Password123!")
        self.user_gestor.groups.add(self.group_gestores)
        self.profile_gestor = UserProfile.objects.create(
            user=self.user_gestor,
            rut="17.892.456-3",
            full_name="Rodrigo Tapia",
            email="gestor@test.cl",
            delegation=self.del_companias
        )

        # 4. Catálogo
        self.catalog = ServiceCatalog.objects.create(
            area="Operativo",
            service="Retiro de Microbasurales",
            attention_type="Coordinación terreno"
        )

    def test_audit_fields_exist(self):
        """Verifica que BaseModel registre created_at, updated_at y deleted_at."""
        act = Activity.objects.create(
            activity_code="ACT-TEST-001",
            activity_date=date.today(),
            problem_description="Test de auditoría",
            executed_action="Acción de prueba",
            delegation=self.del_companias,
            catalog=self.catalog
        )
        self.assertIsNotNone(act.created_at)
        self.assertIsNotNone(act.updated_at)
        self.assertIsNone(act.deleted_at)

    def test_future_date_validation_rejected(self):
        """Verifica que clean() rechace actividades con fechas futuras (Admin Pro)."""
        future_date = date.today() + timedelta(days=5)
        act = Activity(
            activity_code="ACT-TEST-002",
            activity_date=future_date,
            problem_description="Fecha inválida futura",
            executed_action="Intento fallido",
            delegation=self.del_companias,
            catalog=self.catalog
        )
        with self.assertRaises(ValidationError):
            act.clean()

    def test_collective_agenda_requires_contact(self):
        """Verifica que derivar a agenda colectiva exija nombre de contacto."""
        act = Activity(
            activity_code="ACT-TEST-003",
            activity_date=date.today(),
            problem_description="Sin contacto",
            executed_action="Intento fallido",
            is_collective_agenda=True,
            contact_name="",
            delegation=self.del_companias,
            catalog=self.catalog
        )
        with self.assertRaises(ValidationError):
            act.clean()

    def test_soft_delete_audit(self):
        """Verifica que el borrado lógico registre deleted_at sin borrar el registro."""
        act = Activity.objects.create(
            activity_code="ACT-TEST-004",
            activity_date=date.today(),
            problem_description="Registro a eliminar lógicamente",
            executed_action="Borrado de prueba",
            delegation=self.del_companias,
            catalog=self.catalog
        )
        from django.utils import timezone
        act.deleted_at = timezone.now()
        act.save()
        self.assertIsNotNone(Activity.objects.get(activity_code="ACT-TEST-004").deleted_at)

    def test_user_roles_and_scoping(self):
        """Verifica diferenciación de roles: Administrador vs Gestor Limitado."""
        self.assertTrue(self.user_admin.is_superuser)
        self.assertIn("Administradores", [g.name for g in self.user_admin.groups.all()])

        self.assertFalse(self.user_gestor.is_superuser)
        self.assertEqual(self.user_gestor.profile.delegation.name, "Delegación Las Compañías")
        self.assertIn("Gestores Territoriales", [g.name for g in self.user_gestor.groups.all()])

    def test_social_case_future_date_rejected(self):
        """Verifica que clean() rechace casos sociales con fecha futura."""
        from social.models import SocialCase
        future_date = date.today() + timedelta(days=2)
        case = SocialCase(
            user_rut="11.222.333-4",
            user_name="Vecino Test",
            delegation=self.del_companias,
            entry_date=future_date
        )
        with self.assertRaises(ValidationError):
            case.clean()

    def test_social_management_stage_boundary(self):
        """Verifica que clean() restrinja etapas de gestión entre 1 y 3 (RN-012)."""
        from social.models import SocialCase, SocialManagement
        case = SocialCase.objects.create(
            user_rut="12.333.444-5",
            user_name="Caso Test",
            delegation=self.del_companias,
            entry_date=date.today()
        )
        invalid_mgmt = SocialManagement(
            case=case,
            stage=4,  # Mayor a 3
            management_type="Derivación",
            management_date=date.today(),
            result="Prueba inválida"
        )
        with self.assertRaises(ValidationError):
            invalid_mgmt.clean()

    def test_collective_agenda_closing_date_validation(self):
        """Verifica que clean() rechace fecha de cierre anterior a fecha comprometida."""
        from agenda.models import CollectiveAgenda
        agenda = CollectiveAgenda(
            requester="JJVV Test",
            territory="Sector 1",
            delegation=self.del_companias,
            committed_date=date(2026, 4, 15),
            closing_date=date(2026, 4, 10),  # Anterior a committed_date
            description="Compromiso de prueba"
        )
        with self.assertRaises(ValidationError):
            agenda.clean()

