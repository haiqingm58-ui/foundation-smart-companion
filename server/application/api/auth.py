from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select

from ..errors import APIError
from ..models import CaptchaRecord, LoginAttempt, SessionToken, User
from ..security import hash_password, keyed_digest, random_token, token_digest, verify_password
from ..services.captcha import create_captcha
from .dependencies import CSRF_COOKIE, SESSION_COOKIE, AuthContext, current_auth


router = APIRouter(prefix="/api/auth", tags=["authentication"])


class LoginBody(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=200)
    role: str = Field(pattern="^(student|teacher|admin)$")
    captchaId: str = Field(min_length=1, max_length=80)
    captchaCode: str = Field(min_length=4, max_length=8)


class ChangePasswordBody(BaseModel):
    currentPassword: str = Field(min_length=1, max_length=200)
    newPassword: str = Field(min_length=8, max_length=128)

    @field_validator("newPassword")
    @classmethod
    def strong_password(cls, value: str) -> str:
        if not any(char.islower() for char in value) or not any(char.isupper() for char in value) or not any(char.isdigit() for char in value):
            raise ValueError("密码必须包含大写字母、小写字母和数字")
        return value


def client_ip(request: Request) -> str:
    direct = request.client.host if request.client else "unknown"
    forwarded = request.headers.get("X-Real-IP")
    return forwarded if forwarded and direct in {"127.0.0.1", "::1", "testclient"} else direct


def user_payload(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "role": user.role,
        "roleLabel": user.role_label,
        "name": user.name,
        "avatar": user.avatar,
        "studentNo": user.student_no,
        "college": user.college,
        "school": user.school,
        "mentor": user.mentor,
        "mustChangePassword": user.must_change_password,
    }


@router.get("/captcha")
def captcha(request: Request):
    database = request.app.state.database
    settings = request.app.state.settings
    ip = client_ip(request)
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=1)
    with database.session() as session:
        recent = session.scalar(
            select(func.count(CaptchaRecord.id)).where(CaptchaRecord.client_ip == ip, CaptchaRecord.created_at >= cutoff)
        )
        if (recent or 0) >= 30:
            raise APIError(429, "验证码请求过于频繁", "CAPTCHA_RATE_LIMITED")
        record, image = create_captcha(session, settings.secret_key, ip, settings.captcha_ttl_seconds)
    return request.app.state.success(
        request,
        {"captchaId": record.id, "image": image, "expiresIn": settings.captcha_ttl_seconds},
    )


@router.post("/login")
def login(body: LoginBody, request: Request):
    database = request.app.state.database
    settings = request.app.state.settings
    now = datetime.now(timezone.utc)
    ip = client_ip(request)
    with database.session() as session:
        captcha_record = session.get(CaptchaRecord, body.captchaId)
        if not captcha_record:
            raise APIError(400, "验证码不存在，请刷新", "CAPTCHA_INVALID")
        if captcha_record.used_at:
            raise APIError(400, "验证码已使用，请刷新", "CAPTCHA_USED")
        captcha_record.used_at = now
        session.commit()
        if captcha_record.expires_at.tzinfo is None:
            captcha_record.expires_at = captcha_record.expires_at.replace(tzinfo=timezone.utc)
        if captcha_record.expires_at <= now:
            raise APIError(400, "验证码已过期，请刷新", "CAPTCHA_EXPIRED")
        expected = keyed_digest(body.captchaCode.upper(), settings.secret_key)
        if expected != captcha_record.answer_hash:
            raise APIError(400, "验证码错误，请重新输入", "CAPTCHA_INVALID")

        lock_cutoff = now - timedelta(seconds=30)
        failures = session.scalar(
            select(func.count(LoginAttempt.id)).where(
                LoginAttempt.username == body.username.strip(),
                LoginAttempt.success.is_(False),
                LoginAttempt.created_at >= lock_cutoff,
            )
        )
        if (failures or 0) >= 5:
            raise APIError(429, "登录尝试过于频繁，请稍后再试", "LOGIN_LOCKED")

        user = session.scalar(select(User).where(User.username == body.username.strip()))
        valid = False
        needs_rehash = False
        if user:
            valid, needs_rehash = verify_password(body.password, user.password_hash, user.password_algorithm, user.password_salt)
        if not user or not valid:
            session.add(LoginAttempt(id=str(uuid4()), username=body.username.strip(), client_ip=ip, success=False, reason="invalid_credentials"))
            session.commit()
            raise APIError(401, "账号或密码错误", "INVALID_CREDENTIALS")
        if user.status != "active":
            raise APIError(403, "账号已停用，请联系管理员", "ACCOUNT_DISABLED")
        if user.role != body.role:
            raise APIError(403, "所选角色与账号不一致", "ROLE_MISMATCH")
        if needs_rehash:
            user.password_hash = hash_password(body.password)
            user.password_salt = None
            user.password_algorithm = "argon2"

        session_token = random_token()
        csrf_token = random_token(20)
        expires_at = now + timedelta(seconds=settings.session_ttl_seconds)
        session.add(
            SessionToken(
                id=str(uuid4()), user_id=user.id, token_hash=token_digest(session_token),
                csrf_hash=token_digest(csrf_token), expires_at=expires_at,
            )
        )
        session.add(LoginAttempt(id=str(uuid4()), username=user.username, client_ip=ip, success=True, reason="success"))
        user.last_login_at = now
        session.commit()
        payload = user_payload(user)

    response = request.app.state.success(request, {"user": payload, "expiresIn": settings.session_ttl_seconds})
    response.set_cookie(
        SESSION_COOKIE, session_token, max_age=settings.session_ttl_seconds, httponly=True,
        secure=settings.cookie_secure, samesite="lax", path=settings.cookie_path,
    )
    response.set_cookie(
        CSRF_COOKIE, csrf_token, max_age=settings.session_ttl_seconds, httponly=False,
        secure=settings.cookie_secure, samesite="lax", path=settings.cookie_path,
    )
    return response


@router.get("/me")
def me(request: Request, auth: AuthContext = Depends(current_auth)):
    return request.app.state.success(request, {"user": user_payload(auth.user)})


@router.post("/logout")
def logout(request: Request, auth: AuthContext = Depends(current_auth)):
    database = request.app.state.database
    with database.session() as session:
        record = session.get(SessionToken, auth.session.id)
        if record:
            record.revoked_at = datetime.now(timezone.utc)
            session.commit()
    response = request.app.state.success(request, {})
    response.delete_cookie(SESSION_COOKIE, path=request.app.state.settings.cookie_path)
    response.delete_cookie(CSRF_COOKIE, path=request.app.state.settings.cookie_path)
    return response


@router.post("/change-password")
def change_password(body: ChangePasswordBody, request: Request, auth: AuthContext = Depends(current_auth)):
    database = request.app.state.database
    with database.session() as session:
        user = session.get(User, auth.user.id)
        valid, _needs_rehash = verify_password(
            body.currentPassword, user.password_hash, user.password_algorithm, user.password_salt
        )
        if not valid:
            raise APIError(400, "当前密码不正确", "CURRENT_PASSWORD_INVALID")
        if body.currentPassword == body.newPassword:
            raise APIError(400, "新密码不能与当前密码相同", "PASSWORD_UNCHANGED")
        user.password_hash = hash_password(body.newPassword)
        user.password_algorithm = "argon2"
        user.password_salt = None
        user.must_change_password = False
        session.commit()
    return request.app.state.success(request, {"mustChangePassword": False}, "密码修改成功")
