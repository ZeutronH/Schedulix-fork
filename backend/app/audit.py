from datetime import date, datetime
from uuid import UUID
from app.models import AuditLog


def _make_serializable(val):
    if isinstance(val, (date, datetime)):
        return val.isoformat()
    if isinstance(val, UUID):
        return str(val)
    if isinstance(val, dict):
        return {str(k): _make_serializable(v) for k, v in val.items()}
    if isinstance(val, (list, tuple, set)):
        return [_make_serializable(x) for x in val]
    return val


def record_audit(
    db,
    action: str,
    entity_type: str,
    entity_id: str | None = None,
    admin_id: str | None = None,
    details: dict | None = None
):
    safe_details = _make_serializable(details or {})
    entry = AuditLog(
        admin_id=admin_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=safe_details
    )

    db.add(entry)
    db.flush()

    return entry