import uuid
from datetime import datetime, timedelta

import pyotp
import pyotp.totp as pyotp_totp
import pytest
from flask import url_for

from app import db
from app.modules.auth.models import RoleType, User
from app.modules.auth.repositories import UserRepository
from app.modules.auth.services import AuthenticationService
from app.modules.profile.models import UserProfile
from app.modules.profile.repositories import UserProfileRepository


@pytest.fixture(scope="function")
def test_client(test_client):
    with test_client.application.app_context():
        # Add HERE new elements to the database that you want to exist in the test context.
        # DO NOT FORGET to use db.session.add(<element>) and db.session.commit() to save the data.
        user = User.query.filter_by(email="test@example.com").first()
        if user:
            if not user.profile:
                user.profile = UserProfile(name="Test", surname="User")
            user.profile.enabled_two_factor = False
            db.session.add(user)
            db.session.commit()

    yield test_client


def test_login_success(test_client):
    response = test_client.post(
        "/login", data=dict(email="test@example.com", password="test1234"), follow_redirects=True
    )
    assert response.request.path != url_for("auth.login"), "Login was unsuccessful"
    test_client.get("/logout", follow_redirects=True)


def test_login_unsuccessful_bad_email(test_client):
    response = test_client.post(
        "/login", data=dict(email="bademail@example.com", password="test1234"), follow_redirects=True
    )
    assert response.request.path == url_for("auth.login"), "Login was unsuccessful"

    test_client.get("/logout", follow_redirects=True)


def test_login_unsuccessful_bad_password(test_client):
    response = test_client.post(
        "/login", data=dict(email="test@example.com", password="basspassword"), follow_redirects=True
    )
    assert response.request.path == url_for("auth.login"), "Login was unsuccessful"

    test_client.get("/logout", follow_redirects=True)


def test_signup_user_no_name(test_client):
    response = test_client.post(
        "/signup", data=dict(surname="Foo", email="test@example.com", password="test1234"), follow_redirects=True
    )
    assert response.request.path == url_for("auth.show_signup_form"), "Signup was unsuccessful"
    assert b"This field is required" in response.data, response.data


def test_signup_user_unsuccessful(test_client):
    email = "test@example.com"
    response = test_client.post(
        "/signup", data=dict(name="Test", surname="Foo", email=email, password="test1234"), follow_redirects=True
    )
    assert response.request.path == url_for("auth.show_signup_form"), "Signup was unsuccessful"
    assert f"Email {email} in use".encode("utf-8") in response.data


def test_signup_user_successful(test_client):
    response = test_client.post(
        "/signup",
        data=dict(name="Foo", surname="Example", email="foo@example.com", password="foo1234"),
        follow_redirects=True,
    )
    assert response.request.path == url_for("public.index"), "Signup was unsuccessful"


def test_service_create_with_profie_success(clean_database):
    data = {"name": "Test", "surname": "Foo", "email": "service_test@example.com", "password": "test1234"}

    AuthenticationService().create_with_profile(**data)

    assert UserRepository().count() == 1
    assert UserProfileRepository().count() == 1


def test_service_create_with_profile_fail_no_email(clean_database):
    data = {"name": "Test", "surname": "Foo", "email": "", "password": "1234"}

    with pytest.raises(ValueError, match="Email is required."):
        AuthenticationService().create_with_profile(**data)

    assert UserRepository().count() == 0
    assert UserProfileRepository().count() == 0


def test_service_create_with_profile_fail_no_password(clean_database):
    data = {"name": "Test", "surname": "Foo", "email": "test@example.com", "password": ""}

    with pytest.raises(ValueError, match="Password is required."):
        AuthenticationService().create_with_profile(**data)

    assert UserRepository().count() == 0
    assert UserProfileRepository().count() == 0


def test_forgot_password_get(test_client):
    response = test_client.get("/forgot-password")
    assert response.status_code == 200
    assert b"forgot_password" in response.data or b"email" in response.data


def test_forgot_password_post_user_not_found(test_client):
    response = test_client.post("/forgot-password", data=dict(email="nonexistent@example.com"), follow_redirects=True)
    assert response.status_code == 200
    assert b"Correo no registrado" in response.data


def test_forgot_password_post_success(test_client):
    response = test_client.post("/forgot-password", data=dict(email="test@example.com"), follow_redirects=True)
    assert response.status_code == 200


def test_send_password_reset_email_sets_token_and_sends_mail(test_client, monkeypatch):
    service = AuthenticationService()
    email = f"reset+{uuid.uuid4().hex[:8]}@example.com"
    user = service.create_with_profile(name="Recovery", surname="Flow", email=email, password="test1234")

    captured = {}

    def fake_send(message):
        captured["message"] = message

    monkeypatch.setattr("app.modules.auth.services.mail.send", fake_send)
    before = datetime.utcnow()
    service.send_password_reset_email(user)

    assert user.reset_token
    assert user.token_expiration and user.token_expiration > before
    message = captured.get("message")
    assert message is not None
    assert message.recipients == [email]
    assert user.reset_token in (message.html or message.body)


def test_reset_password_view_returns_error_for_invalid_token(test_client, monkeypatch):
    captured = {}

    def fake_render(template_name, **context):
        captured["template"] = template_name
        captured["context"] = context
        return "template stub"

    monkeypatch.setattr("app.modules.auth.routes.render_template", fake_render)
    response = test_client.get("/reset-password/invalid-token")
    assert response.status_code == 200
    assert captured["template"] == "reset_password.html"
    assert captured["context"]["error"] == "Token inválido o expirado."


def test_reset_password_view_rejects_expired_token(test_client, monkeypatch):
    service = AuthenticationService()
    email = f"expired+{uuid.uuid4().hex[:8]}@example.com"
    user = service.create_with_profile(name="Expired", surname="Token", email=email, password="test1234")
    token = "expired-token"
    user.reset_token = token
    user.token_expiration = datetime.utcnow() - timedelta(minutes=5)
    db.session.commit()

    captured = {}

    def fake_render(template_name, **context):
        captured["template"] = template_name
        captured["context"] = context
        return "template stub"

    monkeypatch.setattr("app.modules.auth.routes.render_template", fake_render)
    response = test_client.get(f"/reset-password/{token}")
    assert response.status_code == 200
    assert captured["template"] == "reset_password.html"
    assert captured["context"]["error"] == "Token inválido o expirado."


def test_reset_password_view_updates_password_and_clears_token(test_client):
    service = AuthenticationService()
    email = f"reset-success+{uuid.uuid4().hex[:8]}@example.com"
    user = service.create_with_profile(name="Recover", surname="Success", email=email, password="test1234")
    token = "valid-token"
    user.reset_token = token
    user.token_expiration = datetime.utcnow() + timedelta(hours=1)
    db.session.commit()

    new_password = "brandnew1234"
    response = test_client.post(
        f"/reset-password/{token}",
        data=dict(password=new_password),
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers.get("Location", "").endswith(url_for("auth.login"))
    db.session.refresh(user)
    assert user.check_password(new_password)
    assert user.reset_token is None
    assert user.token_expiration is None


def test_admin_roles_unauthorized_access(test_client):
    test_client.post("/login", data=dict(email="test@example.com", password="test1234"), follow_redirects=True)
    response = test_client.get("/admin_roles", follow_redirects=True)
    assert response.request.path == url_for("public.index"), "Non-admin should be redirected"
    test_client.get("/logout", follow_redirects=True)


def test_admin_roles_without_login(test_client):
    response = test_client.get("/admin_roles", follow_redirects=True)
    assert response.request.path != url_for("auth.admin_roles"), "Unauthenticated user should not access admin_roles"


def test_update_roles_unauthorized(test_client):
    test_client.post("/login", data=dict(email="test@example.com", password="test1234"), follow_redirects=True)
    response = test_client.post("/update_roles", data={"role_1": "administrator"}, follow_redirects=True)
    assert response.request.path != url_for("auth.admin_roles"), "Non-admin should be redirected"
    test_client.get("/logout", follow_redirects=True)


def test_admin_roles_success_as_admin(test_client):
    admin = User.query.filter_by(email="admin@test.com").first()
    if not admin:
        admin = User(email="admin@test.com", password="test1234", role=RoleType.ADMINISTRATOR)
        admin.profile = UserProfile(name="Admin", surname="User")
        admin.profile.enabled_two_factor = False
        db.session.add(admin)
        db.session.commit()

    login_response = test_client.post(
        "/login",
        data=dict(email="admin@test.com", password="test1234"),
        follow_redirects=True,
    )

    assert login_response.request.path == url_for("public.index"), "El login del admin falló"

    response = test_client.get("/admin_roles", follow_redirects=True)

    assert response.status_code == 200
    assert response.request.path == url_for("auth.admin_roles"), "El admin debería poder acceder a la página de roles"
    test_client.get("/logout", follow_redirects=True)

@pytest.fixture
def two_factor_user(test_client):
    service = AuthenticationService()
    email = f"twofactor+{uuid.uuid4().hex[:8]}@example.com"
    user = service.create_with_profile(
        name="Two",
        surname="Factor",
        email=email,
        password="test1234",
    )
    user.profile.enabled_two_factor = True
    db.session.commit()
    return user


@pytest.fixture
def two_factor_user_with_token(two_factor_user):
    secret = pyotp.random_base32()
    two_factor_user.token = secret
    db.session.commit()
    return two_factor_user


def test_generate_qr_code_yields_qr_and_secret(two_factor_user):
    qr_image, token = AuthenticationService().generate_qr_code(two_factor_user)
    assert hasattr(qr_image, "size")
    assert isinstance(token, str)
    assert len(token) >= 16


def test_set_user_token_accepts_valid_code(two_factor_user):
    service = AuthenticationService()
    secret = pyotp.random_base32()
    code = pyotp.TOTP(secret).now()
    service.set_user_token(two_factor_user, secret, code)
    assert two_factor_user.token == secret


FIXED_TOTP_TIME = 1234567890
FIXED_SECRET = "JBSWY3DPEHPK3PXP"


def _invalid_code_for(secret):
    code = pyotp.TOTP(secret).now()
    next_value = (int(code) + 1) % 1000000
    return str(next_value).zfill(6)


def test_set_user_token_rejects_invalid_code(two_factor_user, monkeypatch):
    monkeypatch.setattr(pyotp_totp.time, "time", lambda: FIXED_TOTP_TIME)
    service = AuthenticationService()
    invalid_code = _invalid_code_for(FIXED_SECRET)
    with pytest.raises(ValueError, match="Invalid authentication code."):
        service.set_user_token(two_factor_user, FIXED_SECRET, invalid_code)
    assert two_factor_user.token is None


def test_verify_token_respects_secret(two_factor_user, monkeypatch):
    monkeypatch.setattr(pyotp_totp.time, "time", lambda: FIXED_TOTP_TIME)
    service = AuthenticationService()
    two_factor_user.token = FIXED_SECRET
    db.session.commit()
    valid_code = pyotp.TOTP(FIXED_SECRET).now()
    assert service.verify_token(two_factor_user, valid_code)
    invalid_code = _invalid_code_for(FIXED_SECRET)
    assert not service.verify_token(two_factor_user, invalid_code)


def test_login_requires_two_factor(test_client, two_factor_user):
    response = test_client.post(
        "/login", data=dict(email=two_factor_user.email, password="test1234"), follow_redirects=False
    )
    assert response.status_code == 200
    assert b"Two-Factor Authentication Required" in response.data
    with test_client.session_transaction() as session:
        assert session["pending_user_id"] == two_factor_user.id
        assert "temp_token" in session
    test_client.get("/logout", follow_redirects=True)


def _initiate_two_factor_flow(test_client, user):
    response = test_client.post("/login", data=dict(email=user.email, password="test1234"), follow_redirects=False)
    assert response.status_code == 200
    with test_client.session_transaction() as session:
        assert session.get("pending_user_id") == user.id
        assert "temp_token" in session
    return response


def test_login_handles_missing_pending_user_session(test_client):
    with test_client.session_transaction() as session:
        session["pending_user_id"] = 999999
        session["remember_me"] = True
        session["temp_token"] = "fake-token"

    response = test_client.post("/login", data=dict(code="123456"), follow_redirects=True)
    assert response.status_code == 200
    assert b"Session expired. Please login again." in response.data
    with test_client.session_transaction() as session:
        assert "pending_user_id" not in session
        assert "temp_token" not in session
        assert "remember_me" not in session


def test_login_rejects_non_six_digit_code(test_client, two_factor_user):
    _initiate_two_factor_flow(test_client, two_factor_user)
    response = test_client.post("/login", data=dict(code="123"), follow_redirects=True)
    assert response.status_code == 200
    assert b"Please enter a valid 6-digit code." in response.data
    with test_client.session_transaction() as session:
        assert session.get("pending_user_id") == two_factor_user.id
        assert "temp_token" in session
    test_client.get("/logout", follow_redirects=True)


def test_login_handles_invalid_code_during_token_setup(test_client, two_factor_user, monkeypatch):
    _initiate_two_factor_flow(test_client, two_factor_user)

    def raise_error(self, user, token, code):
        raise ValueError("Invalid authentication code.")

    monkeypatch.setattr(AuthenticationService, "set_user_token", raise_error)
    response = test_client.post("/login", data=dict(code="000000"), follow_redirects=True)
    assert response.status_code == 200
    assert b"Invalid authentication code. Please try again." in response.data
    assert b"data:image/png;base64" in response.data
    with test_client.session_transaction() as session:
        assert session.get("pending_user_id") == two_factor_user.id
        assert "temp_token" in session
    test_client.get("/logout", follow_redirects=True)


def test_login_get_shows_qr_for_pending_user(test_client, two_factor_user):
    _initiate_two_factor_flow(test_client, two_factor_user)
    response = test_client.get("/login")
    assert response.status_code == 200
    assert b"Two-Factor Authentication Required" in response.data
    assert b"data:image/png;base64," in response.data
    with test_client.session_transaction() as session:
        assert session.get("pending_user_id") == two_factor_user.id
        assert "temp_token" in session
    test_client.get("/logout", follow_redirects=True)


def test_login_sets_token_and_redirects_after_code(test_client, two_factor_user):
    test_client.post("/login", data=dict(email=two_factor_user.email, password="test1234"), follow_redirects=False)
    with test_client.session_transaction() as session:
        temp_token = session["temp_token"]
    code = pyotp.TOTP(temp_token).now()
    response = test_client.post("/login", data=dict(code=code), follow_redirects=True)
    assert response.request.path == url_for("public.index")
    with test_client.session_transaction() as session:
        assert "pending_user_id" not in session
        assert "temp_token" not in session
    db.session.refresh(two_factor_user)
    assert two_factor_user.token == temp_token
    test_client.get("/logout", follow_redirects=True)


def test_login_shows_error_for_invalid_code(test_client, two_factor_user_with_token, monkeypatch):
    test_client.post(
        "/login", data=dict(email=two_factor_user_with_token.email, password="test1234"), follow_redirects=False
    )

    def always_fail(self, otp, for_time=None, valid_window=0):
        return False

    monkeypatch.setattr(pyotp.TOTP, "verify", always_fail)
    code = pyotp.TOTP(two_factor_user_with_token.token).now()
    response = test_client.post("/login", data=dict(code=code), follow_redirects=True)
    assert response.status_code == 200
    assert b"Invalid authentication code. Please try again." in response.data
    with test_client.session_transaction() as session:
        assert session.get("pending_user_id") == two_factor_user_with_token.id
    test_client.get("/logout", follow_redirects=True)


def test_login_skips_two_factor_when_disabled(test_client, clean_database):
    email = f"no2fa+{uuid.uuid4().hex[:8]}@example.com"
    service = AuthenticationService()
    user = service.create_with_profile(name="No", surname="TwoFA", email=email, password="safe1234")
    user.profile.enabled_two_factor = False
    db.session.commit()

    response = test_client.post("/login", data=dict(email=email, password="safe1234"), follow_redirects=True)
    assert response.request.path == url_for("public.index")

    with test_client.session_transaction() as session:
        assert session.get("pending_user_id") is None
        assert "temp_token" not in session


def test_login_wrong_password_does_not_trigger_two_factor(test_client, two_factor_user):
    test_client.get("/logout", follow_redirects=True)
    response = test_client.post(
        "/login", data=dict(email=two_factor_user.email, password="wrong"), follow_redirects=True
    )
    assert response.status_code == 200
    assert b"Invalid credentials" in response.data

    with test_client.session_transaction() as session:
        assert session.get("pending_user_id") is None
        assert "temp_token" not in session


def test_existing_token_remains_after_two_factor_login(test_client, two_factor_user_with_token):
    original_token = two_factor_user_with_token.token
    test_client.post(
        "/login", data=dict(email=two_factor_user_with_token.email, password="test1234"), follow_redirects=False
    )
    assert original_token is not None

    code = pyotp.TOTP(original_token).now()
    response = test_client.post("/login", data=dict(code=code), follow_redirects=True)
    assert response.request.path == url_for("public.index")

    db.session.refresh(two_factor_user_with_token)
    assert two_factor_user_with_token.token == original_token


def test_logout_clears_two_factor_session(test_client, two_factor_user):
    test_client.get("/logout", follow_redirects=True)
    test_client.post("/login", data=dict(email=two_factor_user.email, password="test1234"), follow_redirects=False)
    with test_client.session_transaction() as session:
        assert session.get("pending_user_id") == two_factor_user.id
        assert "temp_token" in session

    response = test_client.get("/logout", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers.get("Location") and response.headers["Location"].endswith(url_for("public.index"))

    with test_client.session_transaction() as session:
        assert "pending_user_id" not in session
        assert "temp_token" not in session
