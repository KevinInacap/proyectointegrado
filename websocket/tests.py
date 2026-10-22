from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from channels.testing import WebsocketCommunicator
from config.asgi import application
from organization.models import Delegation, Position, UserProfile
from websocket.services import publish_chat_message

User = get_user_model()


class WebsocketChatTests(TestCase):
    def setUp(self):
        self.del_1, _ = Delegation.objects.get_or_create(name="Delegacion Test 1", defaults={"scope": "Territorio 1"})
        self.del_2, _ = Delegation.objects.get_or_create(name="Delegacion Test 2", defaults={"scope": "Territorio 2"})
        self.pos, _ = Position.objects.get_or_create(name="Gestor Territorial", defaults={"status": "Activo"})

        # Usuario A (Delegación 1)
        self.user_a = User.objects.create_user(username="test_a", password="Password123!")
        UserProfile.objects.create(
            user=self.user_a, rut="11.111.111-1", full_name="User A",
            email="a@test.cl", delegation=self.del_1, position=self.pos, status="Activo"
        )

        # Usuario B (Misma delegación: Delegación 1)
        self.user_b = User.objects.create_user(username="test_b", password="Password123!")
        UserProfile.objects.create(
            user=self.user_b, rut="22.222.222-2", full_name="User B",
            email="b@test.cl", delegation=self.del_1, position=self.pos, status="Activo"
        )

        # Usuario C (Otra delegación: Delegación 2)
        self.user_c = User.objects.create_user(username="test_c", password="Password123!")
        UserProfile.objects.create(
            user=self.user_c, rut="33.333.333-3", full_name="User C",
            email="c@test.cl", delegation=self.del_2, position=self.pos, status="Activo"
        )

    def test_chat_room_view_requires_login(self):
        client = Client()
        response = client.get(reverse("websocket:chat"))
        self.assertEqual(response.status_code, 302)

    def test_chat_room_view_authenticated(self):
        client = Client()
        client.login(username="test_a", password="Password123!")
        response = client.get(reverse("websocket:chat"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Chat de la organización")

    def test_send_message_http_post(self):
        client = Client()
        client.login(username="test_a", password="Password123!")
        response = client.post(reverse("websocket:send"), {"message": "Hola equipo"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"ok": True})

    def test_send_message_invalid_empty(self):
        client = Client()
        client.login(username="test_a", password="Password123!")
        response = client.post(reverse("websocket:send"), {"message": ""})
        self.assertEqual(response.status_code, 400)

    async def test_websocket_connection_unauthenticated_rejected(self):
        communicator = WebsocketCommunicator(application, "/ws/chat/")
        connected, _ = await communicator.connect()
        # Usuario anónimo debe ser cerrado
        self.assertFalse(connected)
        await communicator.disconnect()
