from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.models.user import User


def record(db: Session, *, actor: User, action: str, target_type: str, target_id: int | str, reason: str, previous_value: dict[str, object] | None = None, new_value: dict[str, object] | None = None) -> AuditLog:
    item = AuditLog(actor_user_id=actor.id, action=action, target_type=target_type, target_id=str(target_id), previous_value=previous_value, new_value=new_value, reason=reason.strip())
    db.add(item)
    db.flush()
    return item


def list_logs(db: Session, *, action: str | None = None, target_type: str | None = None, actor_user_id: int | None = None, limit: int = 200) -> list[AuditLog]:
    query = select(AuditLog)
    if action:
        query = query.where(AuditLog.action == action)
    if target_type:
        query = query.where(AuditLog.target_type == target_type)
    if actor_user_id:
        query = query.where(AuditLog.actor_user_id == actor_user_id)
    return list(db.scalars(query.order_by(AuditLog.created_at.desc(), AuditLog.id.desc()).limit(limit)))
