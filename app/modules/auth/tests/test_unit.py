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
        if user and not user.profile:
            user.profile = UserProfile(name="Test", surname="User")
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
