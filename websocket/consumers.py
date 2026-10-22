from asgiref.sync import async_to_sync
from channels.generic.websocket import JsonWebsocketConsumer
from django.core.exceptions import ObjectDoesNotExist


class ChatConsumer(JsonWebsocketConsumer):
    def connect(self):
        user = self.scope.get("user")
        # 1. Validar autenticación
        if not user or not user.is_authenticated:
            self.close()
            return

        # 2. Identificar organización / delegación
        try:
            profile = getattr(user, "profile", None)
            if profile is None:
                self.close()
                return

            org_id = getattr(profile, "organization_id", None) or getattr(profile, "delegation_id", None)
            if hasattr(profile, "delegation") and profile.delegation:
                org_id = org_id or profile.delegation.id
        except ObjectDoesNotExist:
            self.close()
            return

        if org_id is None:
            self.close()
            return

        # 3. Crear nombre del grupo
        self.group_name = f"chat_org_{org_id}"

        # 4. Unirse al grupo
        async_to_sync(self.channel_layer.group_add)(
            self.group_name,
            self.channel_name
        )
        self.accept()

    def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            async_to_sync(self.channel_layer.group_discard)(
                self.group_name,
                self.channel_name
            )

    # 5. Recibir mensaje del navegador
    def receive_json(self, content):
        mensaje = content.get("mensaje", "") or content.get("message", "")
        if not isinstance(mensaje, str):
            return
        mensaje = mensaje.strip()
        if not mensaje or len(mensaje) > 500:
            return

        username = self.scope["user"].get_username() if hasattr(self.scope.get("user"), "get_username") else str(self.scope.get("user"))

        # 6. Enviar mensaje al grupo
        async_to_sync(self.channel_layer.group_send)(
            self.group_name,
            {
                "type": "chat_event",
                "payload": {
                    "type": "chat_message",
                    "username": username,
                    "usuario": username,
                    "message": mensaje,
                    "mensaje": mensaje,
                }
            }
        )



    # 7. Entregar evento al navegador
    def chat_event(self, event):
        self.send_json(event["payload"])
