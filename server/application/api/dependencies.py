from __future__ import annotations

import hmac
from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import Depends, Request
from sqlalchemy import select

from ..errors import APIError
from ..models import SessionToken, User
from ..security import token_digest


SESSION_COOKIE = "foundation_session"
CSRF_COOKIE = "foundation_csrf"


def aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


@dataclass
class AuthContext:
    user: User
    session: SessionToken


def current_auth(request: Request) -> AuthContext:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise APIError(401, "请先登录", "UNAUTHENTICATED")
    database = request.app.state.database
    with database.session() as session:
        record = session.scalar(select(SessionToken).where(SessionToken.token_hash == token_digest(token)))
        if not record or record.revoked_at or aware(record.expires_at) <= datetime.now(timezone.utc):
            raise APIError(401, "登录状态已失效", "SESSION_EXPIRED")
        user = session.get(User, record.user_id)
        if not user or user.status != "active":
            raise APIError(401, "账号不可用", "ACCOUNT_UNAVAILABLE")
        session.expunge(record)
        session.expunge(user)
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        csrf = request.headers.get("X-CSRF-Token", "")
        if not csrf or not hmac.compare_digest(token_digest(csrf), record.csrf_hash):
            raise APIError(403, "安全校验失败，请刷新页面重试", "CSRF_INVALID")
    return AuthContext(user=user, session=record)


def require_role(*roles: str):
    def dependency(auth: AuthContext = Depends(current_auth)) -> AuthContext:
        if auth.user.role not in roles:
            raise APIError(403, "没有访问该功能的权限", "ROLE_FORBIDDEN")
        return auth

    return dependency


require_student = require_role("student")
require_teacher = require_role("teacher")
require_admin = require_role("admin")
require_teacher_or_admin = require_role("teacher", "admin")
