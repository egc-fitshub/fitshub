import os
import secrets
import socket
import time
from contextlib import contextmanager
from datetime import datetime, timedelta
from uuid import uuid4

import pyotp
import pytest
import requests
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from app import app as flask_app
from app import db, mail
from app.modules.auth.models import RoleType, User
from app.modules.profile.models import UserProfile
from core.environment.host import get_host_for_selenium_testing
from core.selenium.common import close_driver, initialize_driver

TWO_FACTOR_EMAIL = "twofactor@example.com"
TWO_FACTOR_PASSWORD = "test1234"
TWO_FACTOR_SECRET = "JBSWY3DPEHPK3PXP"


def wait_for_page_to_load(driver, timeout=8):
    WebDriverWait(driver, timeout).until(
        lambda driver: driver.execute_script("return document.readyState") == "complete"
    )


def wait_for_text(driver, text, timeout=12):
    WebDriverWait(driver, timeout).until(lambda d: text in d.page_source)


def wait_for_element(driver, locator, timeout=10):
    return WebDriverWait(driver, timeout).until(EC.visibility_of_element_located(locator))


def ensure_two_factor_user():
    with flask_app.app_context():
        user = User.query.filter_by(email=TWO_FACTOR_EMAIL).first()
        if not user:
            user = User(
                email=TWO_FACTOR_EMAIL, password=TWO_FACTOR_PASSWORD, role=RoleType.USER, token=TWO_FACTOR_SECRET
            )
            db.session.add(user)
            db.session.commit()

        if not user.profile:
            profile = UserProfile(
                user_id=user.id,
                name="Two",
                surname="Factor",
                affiliation="Test University",
                orcid="0000-0000-0000-0000",
                enabled_two_factor=True,
            )
            db.session.add(profile)
        else:
            user.profile.enabled_two_factor = True
        user.token = TWO_FACTOR_SECRET
        db.session.commit()
        return user, TWO_FACTOR_SECRET


def generate_unique_email(prefix="selenium") -> str:
    return f"{prefix}-{uuid4().hex[:8]}@example.com"


def get_mailhog_host() -> str:
    override = os.getenv("MAILHOG_HOST")
    if override:
        return override
    return "mailhog" if os.getenv("WORKING_DIR") == "/app/" else "localhost"


def ensure_mailhog_reachable(host: str) -> None:
    try:
        resp = requests.get(f"http://{host}:8025", timeout=2)
        resp.raise_for_status()
    except requests.RequestException as exc:
        pytest.skip(f"MailHog UI not reachable at http://{host}:8025 ({exc})")

    smtp_host = os.getenv("MAIL_SERVER", host)
    smtp_port = int(os.getenv("MAIL_PORT", "25")) if os.getenv("MAIL_PORT") else 25
    try:
        with socket.create_connection((smtp_host, smtp_port), timeout=2):
            pass
    except OSError as exc:
        pytest.skip(f"MailHog SMTP not reachable at {smtp_host}:{smtp_port} ({exc})")


@contextmanager
def silent_mail():
    original_send = mail.send
    mail.send = lambda *args, **kwargs: None
    try:
        yield
    finally:
        mail.send = original_send


def create_temporary_user(email: str | None = None, password: str = "TempPass1234") -> User:
    email = email or generate_unique_email()
    with flask_app.app_context():
        existing = User.query.filter_by(email=email).first()
        if existing:
            db.session.delete(existing)
        user = User(email=email, password=password, role=RoleType.USER)
        db.session.add(user)
        db.session.commit()
        profile = UserProfile(
            user_id=user.id,
            name="Temporary",
            surname="User",
            affiliation="Testing",
            orcid="0000-0000-0000-0000",
            enabled_two_factor=False,
        )
        db.session.add(profile)
        db.session.commit()
        return user


def cleanup_temporary_user(email: str) -> None:
    with flask_app.app_context():
        user = User.query.filter_by(email=email).first()
        if user:
            if user.profile:
                db.session.delete(user.profile)
            db.session.delete(user)
            db.session.commit()


def assign_reset_token_to_user(email: str, token: str | None = None, expires_minutes: int = 30) -> str:
    token = token or secrets.token_urlsafe(24)
    with flask_app.app_context():
        persistent = User.query.filter_by(email=email).first()
        persistent.reset_token = token
        persistent.token_expiration = datetime.utcnow() + timedelta(minutes=expires_minutes)
        db.session.commit()
    return token


def test_login_and_check_element():
    driver = initialize_driver()

    try:
        host = get_host_for_selenium_testing()

        # Open the login page
        driver.get(f"{host}/login")

        wait_for_page_to_load(driver)

        email_field = wait_for_element(driver, (By.NAME, "email"))
        password_field = wait_for_element(driver, (By.NAME, "password"))

        email_field.send_keys("user1@example.com")
        password_field.send_keys("1234")

        # Send the form
        password_field.send_keys(Keys.RETURN)

        wait_for_page_to_load(driver)

        try:
            wait_for_element(driver, (By.XPATH, "//h1[contains(@class, 'h2 mb-3') and contains(., 'Latest datasets')]"))
            print("Test passed!")

        except NoSuchElementException:
            raise AssertionError("Test failed!")

    finally:
        # Close the browser
        close_driver(driver)


def test_two_factor_login_flow():
    ensure_two_factor_user()
    driver = initialize_driver()

    try:
        host = get_host_for_selenium_testing()

        driver.get(f"{host}/login")
        wait_for_page_to_load(driver)

        driver.find_element(By.NAME, "email").send_keys(TWO_FACTOR_EMAIL)
        driver.find_element(By.NAME, "password").send_keys(TWO_FACTOR_PASSWORD)
        driver.find_element(By.ID, "submit").send_keys(Keys.RETURN)
        wait_for_page_to_load(driver)

        secret = TWO_FACTOR_SECRET
        verification_code = pyotp.TOTP(secret).now()
        code_field = wait_for_element(driver, (By.NAME, "code"))
        assert "Two-Factor Authentication Required" in driver.page_source
        code_field.send_keys(verification_code)
        driver.find_element(By.ID, "submit").send_keys(Keys.RETURN)
        wait_for_page_to_load(driver)

        wait_for_element(driver, (By.XPATH, "//h1[contains(@class, 'h2 mb-3') and contains(., 'Latest datasets')]"))
        assert driver.current_url != f"{host}/login"

        driver.get(f"{host}/logout")
        wait_for_page_to_load(driver)
        driver.get(f"{host}/admin_roles")
        wait_for_page_to_load(driver)
        wait_for_element(driver, (By.XPATH, "//h1[contains(@class, 'h2 mb-3') and contains(., 'Login')]"))
        print("2FA login test passed!")
    finally:
        close_driver(driver)


def test_connect_to_mailhog():
    """Test connection to MailHog web interface available in Docker or local setups."""
    host = get_mailhog_host()
    ensure_mailhog_reachable(host)

    driver = initialize_driver()

    try:
        mailhog_url = f"http://{host}:8025"

        # Open the MailHog web interface
        driver.get(mailhog_url)
        time.sleep(4)

        # Search for the text 'mailhog' in the page
        page_text = driver.page_source or ""
        if "mailhog" not in page_text.lower():
            raise AssertionError("MailHog connection test failed: 'mailhog' not found in page")
        print("MailHog connection test passed!")

    finally:
        close_driver(driver)


def test_two_factor_invalid_code_shows_error():
    ensure_two_factor_user()
    driver = initialize_driver()

    try:
        host = get_host_for_selenium_testing()

        driver.get(f"{host}/login")
        wait_for_page_to_load(driver)

        driver.find_element(By.NAME, "email").send_keys(TWO_FACTOR_EMAIL)
        driver.find_element(By.NAME, "password").send_keys(TWO_FACTOR_PASSWORD)
        driver.find_element(By.ID, "submit").send_keys(Keys.RETURN)
        wait_for_page_to_load(driver)

        code_field = wait_for_element(driver, (By.NAME, "code"))
        assert "Two-Factor Authentication Required" in driver.page_source
        code_field.send_keys("000000")
        driver.find_element(By.ID, "submit").send_keys(Keys.RETURN)
        wait_for_page_to_load(driver)

        wait_for_element(driver, (By.XPATH, "//h5[contains(., 'Two-Factor Authentication Required')]"))
        wait_for_element(driver, (By.NAME, "code"))
        print("Invalid 2FA code test passed!")

    finally:
        close_driver(driver)


def test_forgot_password_unknown_email_shows_error():
    driver = initialize_driver()

    try:
        host = get_host_for_selenium_testing()

        driver.get(f"{host}/forgot-password")
        wait_for_page_to_load(driver)

        email_field = wait_for_element(driver, (By.NAME, "email"))
        email_field.send_keys(generate_unique_email("missing"))
        driver.find_element(By.XPATH, "//input[@type='submit']").send_keys(Keys.RETURN)

        wait_for_page_to_load(driver)
        wait_for_element(driver, (By.XPATH, "//*[contains(text(), 'Correo no registrado.')]"))
        print("Forgot password error message test passed!")
    finally:
        close_driver(driver)


def test_forgot_password_mailhog():
    """
    Submit the forgot-password form and verify MailHog received the email.
    Works in Docker or a local environment that exposes MailHog at :8025.
    """
    host = get_mailhog_host()
    ensure_mailhog_reachable(host)

    target_email = generate_unique_email("mailhog")
    create_temporary_user(email=target_email)

    try:
        driver = initialize_driver()
        try:
            selenium_host = get_host_for_selenium_testing()

            # Open the forgot password page and submit the form
            driver.get(f"{selenium_host}/forgot-password")
            time.sleep(2)

            email_field = driver.find_element(By.NAME, "email")
            email_field.clear()
            email_field.send_keys(target_email)
            email_field.send_keys(Keys.RETURN)

            time.sleep(2)
        finally:
            close_driver(driver)

        # Poll MailHog API for the message (up to 20s)
        mailhog_host = host
        api_url = f"http://{mailhog_host}:8025/api/v2/messages"

        found = False
        deadline = time.time() + 20
        while time.time() < deadline:
            resp = requests.get(api_url, timeout=5)
            data = resp.json()

            for item in data.get("items", []):
                headers = item.get("Content", {}).get("Headers", {})
                tos = headers.get("To", [])
                for to in tos:
                    if target_email in to:
                        found = True
                        break
                if found:
                    break

                body = item.get("Content", {}).get("Body", "") or ""
                if target_email in body:
                    found = True
                    break

                if found:
                    break

            time.sleep(1)

        assert found, f"Forgot password email for {target_email} not found in MailHog (checked {api_url})"
    finally:
        cleanup_temporary_user(target_email)


def test_forgot_password_success_sets_token():
    email = generate_unique_email("forgot")
    create_temporary_user(email=email)
    driver = initialize_driver()

    try:
        host = get_host_for_selenium_testing()

        driver.get(f"{host}/forgot-password")
        wait_for_page_to_load(driver)

        email_field = wait_for_element(driver, (By.NAME, "email"))
        email_field.send_keys(email)

        with silent_mail():
            driver.find_element(By.XPATH, "//input[@type='submit']").send_keys(Keys.RETURN)
            wait_for_page_to_load(driver)

            wait_for_text(driver, "Correo de recuperación enviado.")

        with flask_app.app_context():
            refreshed = User.query.filter_by(email=email).first()
            assert refreshed.reset_token
            assert refreshed.token_expiration and refreshed.token_expiration > datetime.utcnow()
        print("Forgot password success test passed!")

    finally:
        cleanup_temporary_user(email)
        close_driver(driver)


def test_reset_password_flow_completes_login():
    email = generate_unique_email("recover")
    original_password = "Original1234!"
    new_password = "BrandNew123!"
    create_temporary_user(email=email, password=original_password)
    token = assign_reset_token_to_user(email)
    driver = initialize_driver()

    try:
        host = get_host_for_selenium_testing()

        driver.get(f"{host}/reset-password/{token}")
        wait_for_page_to_load(driver)

        password_field = wait_for_element(driver, (By.NAME, "password"))
        password_field.send_keys(new_password)
        driver.find_element(By.XPATH, "//input[@type='submit']").send_keys(Keys.RETURN)

        wait_for_page_to_load(driver)
        wait_for_element(driver, (By.XPATH, "//h1[contains(., 'Login')]"))

        driver.find_element(By.NAME, "email").send_keys(email)
        driver.find_element(By.NAME, "password").send_keys(new_password)
        driver.find_element(By.ID, "submit").send_keys(Keys.RETURN)

        wait_for_page_to_load(driver)
        wait_for_element(
            driver,
            (
                By.XPATH,
                "//h1[contains(@class, 'h2 mb-3') and .//b[text()='Latest'] and contains(., 'datasets')]",
            ),
        )
        driver.get(f"{host}/logout")
        wait_for_page_to_load(driver)
        print("Reset password flow test passed!")

    finally:
        cleanup_temporary_user(email)
        close_driver(driver)
