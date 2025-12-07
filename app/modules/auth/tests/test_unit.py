import os
import re
import time
from urllib.parse import urlparse

import pytest
import requests
from flask import url_for

from app.modules.auth.repositories import UserRepository
from app.modules.auth.services import AuthenticationService
from app.modules.profile.repositories import UserProfileRepository


@pytest.fixture(scope="function")
def test_client(test_client):
    with test_client.application.app_context():
        # Add HERE new elements to the database that you want to exist in the test context.
        # DO NOT FORGET to use db.session.add(<element>) and db.session.commit() to save the data.
        pass

    yield test_client


def test_mailhog_reacheable_from_docker():
    if not (os.getenv("WORKING_DIR") == "/app/"):
        pytest.skip("Only runs in Docker environment")
    try:
        host = "mailhog" if os.getenv("WORKING_DIR") == "/app/" else "localhost"
        response = requests.get(f"http://{host}:8025")
        assert response.status_code == 200, "MailHog is not reachable from Docker"
    except requests.ConnectionError:
        assert False, "MailHog is not reachable from Docker"


def test_mailhog_shows_email_sent(test_client):
    if not (os.getenv("WORKING_DIR") == "/app/"):
        pytest.skip("Only runs in Docker environment")

    # Ensure clean inbox
    target_email = "test@example.com"
    host = "mailhog" if os.getenv("WORKING_DIR") == "/app/" else "localhost"
    api_base = f"http://{host}:8025"

    try:
        requests.delete(f"{api_base}/api/v1/messages")
    except requests.ConnectionError:
        assert False, "MailHog is not reachable from Docker"

    # Trigger the email
    response = test_client.post("/forgot-password", data=dict(email=target_email), follow_redirects=True)
    assert response.status_code == 200

    # Poll MailHog API for the message addressed to target_email
    messages = []
    for _ in range(10):
        try:
            r = requests.get(f"{api_base}/api/v2/messages", timeout=2)
        except requests.ConnectionError:
            assert False, "MailHog is not reachable from Docker"

        assert r.status_code == 200, "MailHog API is not reachable"
        messages = r.json().get("items", [])

        # Look for a message whose To header contains the target email
        found = None
        for item in messages:
            headers = item.get("Content", {}).get("Headers", {})
            to_list = headers.get("To", [])
            if any(target_email in t for t in to_list):
                found = item
                break

        if found:
            break
        time.sleep(0.5)

    assert found is not None, "Email not found in MailHog"


def test_mailhog_forgot_password_reset_link_works(test_client):
    if not (os.getenv("WORKING_DIR") == "/app/"):
        pytest.skip("Only runs in Docker environment")

    target_email = "test@example.com"
    host = "mailhog" if os.getenv("WORKING_DIR") == "/app/" else "localhost"
    api_base = f"http://{host}:8025"

    # Ensure clean inbox
    try:
        requests.delete(f"{api_base}/api/v1/messages")
    except requests.ConnectionError:
        pytest.fail("MailHog is not reachable from Docker")

    # Trigger the email
    resp = test_client.post("/forgot-password", data=dict(email=target_email), follow_redirects=True)
    assert resp.status_code == 200

    # Poll MailHog API for the reset link
    found_link = None
    for _ in range(10):
        r = requests.get(f"{api_base}/api/v2/messages", timeout=2)
        assert r.status_code == 200
        items = r.json().get("items", [])
        for item in items:
            headers = item.get("Content", {}).get("Headers", {})
            to_list = headers.get("To", [])
            if any(target_email in t for t in to_list):
                # Get body content
                body = ""
                content = item.get("Content", {}) or {}
                body = content.get("Body", "") or item.get("Raw", {}).get("Data", "") or item.get("Body", "")

                # Find reset link
                m = re.search(r'(https?://[^\s"\']+/reset-password/[^\s"\']+)', body)

                if m:
                    found_link = m.group(1)
                    break
        if found_link:
            break
        time.sleep(0.5)

    assert found_link, "Reset link not found in MailHog message"

    # Follow the link inside the Flask app
    parsed = urlparse(found_link)
    resp2 = test_client.get(parsed.path, follow_redirects=True)
    assert resp2.status_code == 200
    assert b"reset" in resp2.data.lower() or b"token" in resp2.data.lower()


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


"""
def test_admin_roles_success_as_admin(test_client):
    login_response = test_client.post(
        "/login",
        data=dict(email="admin@test.com", password="test1234"),
        follow_redirects=True
    )

    assert login_response.request.path == url_for("public.index"), "El login del admin falló"

    response = test_client.get("/admin_roles", follow_redirects=True)

    assert response.status_code == 200
    assert response.request.path == url_for("auth.admin_roles"), "El admin debería poder acceder a la página de roles"

    assert b"test@example.com" in response.data

    test_client.get("/logout", follow_redirects=True)
"""
