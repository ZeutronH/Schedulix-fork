from unittest.mock import patch

from app.services.whatsapp import WhatsAppService


def test_whatsapp_not_configured():
    with patch(
        "app.services.whatsapp.settings.WHATSAPP_ENABLED",
        False
    ):
        service = WhatsAppService()
        assert service.enabled is False


def test_signature_rejects_invalid_secret():
    service = WhatsAppService()

    assert service.verify_signature(
        b"test payload",
        "sha256=invalid"
    ) is False