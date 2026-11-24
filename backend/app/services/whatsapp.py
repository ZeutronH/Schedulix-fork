import hashlib
import hmac
import httpx

from app.config import settings
from app.models import (
    WhatsAppNotification,
    DeliveryStatus,
    Student,
    Faculty,
)


GRAPH_VERSION = "v23.0"


class WhatsAppService:

    def __init__(self):
        self.enabled = bool(
            settings.WHATSAPP_ENABLED
            and settings.WHATSAPP_ACCESS_TOKEN
            and settings.WHATSAPP_PHONE_NUMBER_ID
        )

        self.base_url = (
            f"https://graph.facebook.com/{GRAPH_VERSION}"
        )

    def _headers(self):
        return {
            "Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}"
        }

    def verify_signature(self, body: bytes, signature: str):
        if not settings.WHATSAPP_APP_SECRET:
            return False

        expected = "sha256=" + hmac.new(
            settings.WHATSAPP_APP_SECRET.encode(),
            body,
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(expected, signature)

    async def upload_image(self, path):
        if not self.enabled:
            raise RuntimeError("WhatsApp API is not configured")

        async with httpx.AsyncClient(timeout=60) as client:
            with open(path, "rb") as file:
                response = await client.post(
                    f"{self.base_url}/"
                    f"{settings.WHATSAPP_PHONE_NUMBER_ID}/media",
                    headers=self._headers(),
                    data={"messaging_product": "whatsapp"},
                    files={
                        "file": (
                            "timetable.png",
                            file,
                            "image/png"
                        )
                    }
                )

            response.raise_for_status()
            return response.json()["id"]

    async def send_image(
        self,
        recipient,
        media_id,
        caption
    ):
        if not self.enabled:
            raise RuntimeError("WhatsApp API is not configured")

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient,
            "type": "image",
            "image": {
                "id": media_id,
                "caption": caption
            }
        }

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self.base_url}/"
                f"{settings.WHATSAPP_PHONE_NUMBER_ID}/messages",
                headers={
                    **self._headers(),
                    "Content-Type": "application/json"
                },
                json=payload
            )

            response.raise_for_status()
            return response.json()

    async def send_template(self, recipient, parameters):
        if not self.enabled:
            raise RuntimeError("WhatsApp API is not configured")

        payload = {
            "messaging_product": "whatsapp",
            "to": recipient,
            "type": "template",
            "template": {
                "name": settings.WHATSAPP_TEMPLATE_NAME,
                "language": {
                    "code": settings.WHATSAPP_TEMPLATE_LANGUAGE
                },
                "components": [{
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": str(p)}
                        for p in parameters
                    ]
                }]
            }
        }

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self.base_url}/"
                f"{settings.WHATSAPP_PHONE_NUMBER_ID}/messages",
                headers=self._headers(),
                json=payload
            )

            response.raise_for_status()
            return response.json()


def update_delivery_status(db, message_id, status, timestamp, payload):
    notification = db.query(
        WhatsAppNotification
    ).filter(
        WhatsAppNotification.message_id == message_id
    ).with_for_update().first()

    if not notification:
        return None

    mapping = {
        "sent": DeliveryStatus.SENT,
        "delivered": DeliveryStatus.DELIVERED,
        "read": DeliveryStatus.READ,
        "failed": DeliveryStatus.FAILED,
    }

    if status in mapping:
        notification.status = mapping[status]

    from app.models import WhatsAppDeliveryEvent

    db.add(
        WhatsAppDeliveryEvent(
            notification_id=notification.id,
            status=status,
            event_timestamp=timestamp,
            payload=payload
        )
    )

    db.flush()
    return notification