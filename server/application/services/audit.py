from __future__ import annotations

from uuid import uuid4

from sqlalchemy.orm import Session

from ..models import OperationLog


def add_log(session: Session, actor_id: str | None, action: str, target_type: str | None = None, target_id: str | None = None, detail: dict | None = None, client_ip: str | None = None) -> None:
    session.add(
        OperationLog(
            id=str(uuid4()), actor_id=actor_id, action=action, target_type=target_type,
            target_id=target_id, detail=detail or {}, client_ip=client_ip,
        )
    )
