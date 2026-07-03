from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select


@pytest.fixture()
def auth_app(database_url: str, monkeypatch: pytest.MonkeyPatch):
    from server.application.config import Settings
    from server.application.database import create_database
    from server.application.main import create_app
    from server.application.migrations import upgrade_database
    from server.application.models import User
    from server.application.security import hash_password
    from server.application.services import captcha as captcha_service

    monkeypatch.setattr(captcha_service, "random_code", lambda: "ABCD")
    upgrade_database(database_url)
    database = create_database(database_url)
    password_hash = hash_password("Correct-123")
    with database.session() as session:
        session.add_all(
            [
                User(
                    id="student-test", username="student-test", password_hash=password_hash,
                    password_algorithm="argon2", role="student", role_label="学生", name="测试学生",
                    student_no="20260001", college="土木工程学院", school="湖南大学", status="active",
                ),
                User(
                    id="teacher-disabled", username="teacher-disabled", password_hash=password_hash,
                    password_algorithm="argon2", role="teacher", role_label="指导老师", name="停用教师",
                    student_no="T0001", college="土木工程学院", school="湖南大学", status="disabled",
                ),
            ]
        )
        session.commit()
    settings = Settings(
        database_url=database_url,
        secret_key="test-secret",
        data_dir=database.engine.url.database,
        upload_dir=database.engine.url.database,
        session_ttl_seconds=3600,
        captcha_ttl_seconds=120,
        cookie_secure=False,
        cookie_path="/",
        llm_api_url="",
        llm_api_key="",
        llm_model="test-model",
    )
    app = create_app(settings=settings, database=database)
    return app, database


def captcha(client: TestClient) -> str:
    response = client.get("/api/auth/captcha")
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["image"].startswith("data:image/png;base64,")
    assert "ABCD" not in response.text
    return payload["data"]["captchaId"]


def login(client: TestClient, captcha_id: str, **overrides):
    body = {
        "username": "student-test",
        "password": "Correct-123",
        "role": "student",
        "captchaId": captcha_id,
        "captchaCode": "abcd",
    }
    body.update(overrides)
    return client.post("/api/auth/login", json=body)


def test_login_me_and_logout_use_revocable_http_only_session(auth_app) -> None:
    app, _database = auth_app
    with TestClient(app) as client:
        response = login(client, captcha(client))
        assert response.status_code == 200
        assert response.json()["data"]["user"]["role"] == "student"
        assert "HttpOnly" in response.headers["set-cookie"]

        me = client.get("/api/auth/me")
        assert me.status_code == 200
        assert me.json()["data"]["user"]["username"] == "student-test"

        csrf = client.cookies.get("foundation_csrf")
        logout = client.post("/api/auth/logout", headers={"X-CSRF-Token": csrf})
        assert logout.status_code == 200
        assert client.get("/api/auth/me").status_code == 401


def test_captcha_is_single_use_even_when_answer_is_wrong(auth_app) -> None:
    app, _database = auth_app
    with TestClient(app) as client:
        captcha_id = captcha(client)
        wrong = login(client, captcha_id, captchaCode="WXYZ")
        assert wrong.status_code == 400
        assert wrong.json()["code"] == "CAPTCHA_INVALID"
        reused = login(client, captcha_id)
        assert reused.status_code == 400
        assert reused.json()["code"] == "CAPTCHA_USED"


def test_expired_captcha_is_rejected(auth_app) -> None:
    from server.application.models import CaptchaRecord

    app, database = auth_app
    with TestClient(app) as client:
        captcha_id = captcha(client)
        with database.session() as session:
            record = session.get(CaptchaRecord, captcha_id)
            record.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
            session.commit()
        response = login(client, captcha_id)
        assert response.status_code == 400
        assert response.json()["code"] == "CAPTCHA_EXPIRED"


def test_role_mismatch_and_disabled_account_are_rejected(auth_app) -> None:
    app, _database = auth_app
    with TestClient(app) as client:
        mismatch = login(client, captcha(client), role="admin")
        assert mismatch.status_code == 403
        assert mismatch.json()["code"] == "ROLE_MISMATCH"
        disabled = login(
            client,
            captcha(client),
            username="teacher-disabled",
            password="Correct-123",
            role="teacher",
        )
        assert disabled.status_code == 403
        assert disabled.json()["code"] == "ACCOUNT_DISABLED"


def test_five_wrong_passwords_temporarily_lock_account(auth_app) -> None:
    app, _database = auth_app
    with TestClient(app) as client:
        for _ in range(5):
            response = login(client, captcha(client), password="wrong-password")
            assert response.status_code == 401
        locked = login(client, captcha(client))
        assert locked.status_code == 429
        assert locked.json()["code"] == "LOGIN_LOCKED"


def test_authenticated_user_changes_password_and_clears_first_login_flag(auth_app) -> None:
    from server.application.models import User
    from server.application.security import verify_password

    app, database = auth_app
    with database.session() as session:
        user = session.get(User, "student-test")
        user.must_change_password = True
        session.commit()
    with TestClient(app) as client:
        assert login(client, captcha(client)).status_code == 200
        csrf = client.cookies.get("foundation_csrf")
        response = client.post(
            "/api/auth/change-password",
            json={"currentPassword": "Correct-123", "newPassword": "Changed-456"},
            headers={"X-CSRF-Token": csrf},
        )
        assert response.status_code == 200
        assert response.json()["data"]["mustChangePassword"] is False
        with database.session() as session:
            user = session.get(User, "student-test")
            assert user.must_change_password is False
            assert verify_password("Changed-456", user.password_hash, user.password_algorithm)[0]
