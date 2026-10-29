from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def publish_chat_message(user, org_id, message):
    layer = get_channel_layer()
    if layer is None:
        raise RuntimeError("Channel layer no configurado")

    username = user.get_username() if hasattr(user, "get_username") else str(user)

    async_to_sync(layer.group_send)(
        f"chat_org_{org_id}",
        {
            "type": "chat_event",
            "payload": {
                "type": "chat_message",
                "username": username,
                "usuario": username,
                "message": message,
                "mensaje": message,
            },
        },
    )


def publish_module_changed(org_id, module_name="registro", action="actualizado", extra=None):
    layer = get_channel_layer()
    if layer is None:
        return

    payload = {
        "type": "crud_update",
        "module": module_name,
        "action": action,
        "message": f"El {module_name} ha sido {action}.",
    }
    if extra:
        payload.update(extra)

    async_to_sync(layer.group_send)(
        f"chat_org_{org_id}",
        {
            "type": "chat_event",
            "payload": payload,
        },
    )
