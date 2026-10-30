import json

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from activities.models import Vecino
from core.models import AuditLog
from organization.models import Position, Role, UserProfile


class EvaluacionCrudVecinosTests(TestCase):
    def test_login_dashboard_y_crud_persistente_con_csrf(self):
        user = get_user_model().objects.create_user(username='admin-evaluacion', password='clave-de-prueba')
        position, _ = Position.objects.get_or_create(name='Administrador General')
        role, _ = Role.objects.get_or_create(name='Administrador', defaults={'is_system': True})
        profile = UserProfile.objects.create(user=user, rut='11223344-5', full_name='Admin Evaluación',
                                             email='evaluacion@example.test', position=position, status='Activo')
        profile.roles.add(role)
        client = Client(enforce_csrf_checks=True)
        login_url = reverse('core:login')
        self.assertEqual(client.get(login_url).status_code, 200)
        token = client.cookies['csrftoken'].value
        login = client.post(login_url, {'username': user.username, 'password': 'clave-de-prueba',
                                        'csrfmiddlewaretoken': token})
        self.assertEqual(login.status_code, 302)
        self.assertEqual(client.get(reverse('activities:dashboard_admin')).status_code, 200)
        token = client.cookies['csrftoken'].value
        url = reverse('activities:api_vecinos')
        payload = {'nombre': 'Vecina de Evaluación', 'rut': '12.345.678-5', 'email': 'vecina@example.test',
                   'direccion': 'Calle de prueba 123', 'telefono': '+56912345678',
                   'territorio': 'Centro', 'estado': 'Activo'}
        denied = client.post(url, json.dumps(payload), content_type='application/json')
        self.assertEqual(denied.status_code, 403)
        created = client.post(url, json.dumps(payload), content_type='application/json', HTTP_X_CSRFTOKEN=token)
        self.assertEqual(created.status_code, 200, created.content)
        neighbor_id = created.json()['vecino']['id']
        self.assertTrue(Vecino.objects.filter(pk=neighbor_id, nombre=payload['nombre']).exists())
        self.assertIn(neighbor_id, [row['id'] for row in client.get(url).json()['vecinos']])
        detail = reverse('activities:api_vecino_detail', args=[neighbor_id])
        edited = client.put(detail, json.dumps({'direccion': 'Calle corregida 456'}),
                            content_type='application/json', HTTP_X_CSRFTOKEN=token)
        self.assertEqual(edited.status_code, 200, edited.content)
        self.assertEqual(Vecino.objects.get(pk=neighbor_id).direccion, 'Calle corregida 456')
        deleted = client.delete(detail, HTTP_X_CSRFTOKEN=token)
        self.assertEqual(deleted.status_code, 200, deleted.content)
        neighbor = Vecino.objects.get(pk=neighbor_id)
        self.assertIsNotNone(neighbor.deleted_at)
        self.assertNotIn(neighbor_id, [row['id'] for row in client.get(url).json()['vecinos']])
        self.assertTrue(AuditLog.objects.filter(affected_table='vecino', affected_record_id=str(neighbor_id), action='DELETE').exists())
