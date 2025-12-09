from contextlib import contextmanager
from uuid import uuid4

import pyotp
from locust import HttpUser, TaskSet, task

from app import app as flask_app
from app import db, mail
from app.modules.auth.models import RoleType, User
from app.modules.profile.models import UserProfile
from core.environment.host import get_host_for_locust_testing
from core.locust.common import fake, get_csrf_token

TWO_FACTOR_EMAIL = "twofactor@example.com"
TWO_FACTOR_PASSWORD = "test1234"
TWO_FACTOR_SECRET = "JBSWY3DPEHPK3PXP"


class SignupBehavior(TaskSet):
    def on_start(self):
        self.ensure_logged_out()
        self.signup()

    def ensure_logged_out(self):
        self.client.get("/logout")

    @task
    def signup(self):
        response = self.client.get("/signup")

        if response.status_code != 200:
            print(f"Signup page unreachable: {response.status_code}")
            return

        try:
            csrf_token = get_csrf_token(response)
        except ValueError as exc:
            print(f"Signup CSRF token missing: {exc}\n{response.text[:300]}")
            return

        response = self.client.post(
            "/signup", data={"email": fake.email(), "password": fake.password(), "csrf_token": csrf_token}
        )
        if response.status_code != 200:
            print(f"Signup failed: {response.status_code}")
        self.ensure_logged_out()


class LoginBehavior(TaskSet):
    def on_start(self):
        self.ensure_logged_out()
        self.login()

    @task
    def ensure_logged_out(self):
        response = self.client.get("/logout")
        if response.status_code != 200:
            print(f"Logout failed or no active session: {response.status_code}")

    @task
    def login(self):
        response = self.client.get("/login")
        if response.status_code != 200 or "Login" not in response.text:
            print("Already logged in or unexpected response, redirecting to logout")
            self.ensure_logged_out()
            response = self.client.get("/login")

        csrf_token = get_csrf_token(response)

        response = self.client.post(
            "/login", data={"email": "user1@example.com", "password": "1234", "csrf_token": csrf_token}
        )
        if response.status_code != 200:
            print(f"Login failed: {response.status_code}")


class TwoFactorLoginBehavior(TaskSet):
    def ensure_logged_out(self):
        self.client.get("/logout")

    def _get_login_page(self):
        response = self.client.get("/login")
        if response.status_code != 200:
            print(f"Unable to reach login page: {response.status_code}")
            return None
        return response

    def _post_login_credentials(self, csrf_token):
        return self.client.post(
            "/login",
            data={"email": TWO_FACTOR_EMAIL, "password": TWO_FACTOR_PASSWORD, "csrf_token": csrf_token},
            allow_redirects=False,
            catch_response=True,
            name="/login 2FA credentials",
        )

    def _post_two_factor_code(self, code, csrf_token):
        return self.client.post(
            "/login",
            data={"code": code, "csrf_token": csrf_token},
            allow_redirects=False,
            catch_response=True,
            name="/login 2FA code",
        )

    def _verify_protected_view(self):
        response = self.client.get("/profile/edit")
        if response.status_code != 200:
            print(f"Protected page check failed: {response.status_code}")

    def _verify_homepage(self):
        response = self.client.get("/")
        if response.status_code != 200:
            print(f"Homepage smoke check failed: {response.status_code}")

    @task
    def login_with_two_factor(self):
        self.ensure_logged_out()

        login_page = self._get_login_page()
        if not login_page:
            return

        try:
            csrf_token = get_csrf_token(login_page)
        except ValueError as exc:
            print(f"Missing CSRF token during credential step: {exc}")
            return

        first_response = self._post_login_credentials(csrf_token)

        if first_response.status_code not in (200, 302):
            first_response.failure("Initial 2FA login request failed")
            return

        two_factor_page = self.client.get("/login")
        if two_factor_page.status_code != 200:
            print(f"Unable to reach two-factor page: {two_factor_page.status_code}")
            return

        try:
            csrf_token = get_csrf_token(two_factor_page)
        except ValueError as exc:
            print(f"Missing CSRF token before submitting 2FA code: {exc}")
            return

        code = pyotp.TOTP(TWO_FACTOR_SECRET).now()

        second_response = self._post_two_factor_code(code, csrf_token)
        if second_response.status_code not in (301, 302):
            second_response.failure("2FA code submission failed")
        else:
            self._verify_protected_view()
            self._verify_homepage()

        self.ensure_logged_out()

    @task
    def login_with_invalid_two_factor_code(self):
        self.ensure_logged_out()

        login_page = self._get_login_page()
        if not login_page:
            return

        try:
            csrf_token = get_csrf_token(login_page)
        except ValueError as exc:
            print(f"Missing CSRF token during invalid code step: {exc}")
            return

        self._post_login_credentials(csrf_token)

        two_factor_page = self.client.get("/login")
        if two_factor_page.status_code != 200:
            print(f"Unable to reach two-factor page for invalid code test: {two_factor_page.status_code}")
            return

        try:
            csrf_token = get_csrf_token(two_factor_page)
        except ValueError as exc:
            print(f"Missing CSRF token before submitting invalid code: {exc}")
            return

        invalid_code = "000000"
        response = self._post_two_factor_code(invalid_code, csrf_token)

        if response.status_code in (301, 302):
            response.failure("Invalid code unexpectedly succeeded")

        self.ensure_logged_out()


@contextmanager
def silent_mail():
    original_send = mail.send
    mail.send = lambda *args, **kwargs: None
    try:
        yield
    finally:
        mail.send = original_send


def create_recovery_user(prefix="locust", password="TempPass1234") -> tuple[str, str]:
    email = f"{prefix}-{uuid4().hex[:8]}@example.com"
    with flask_app.app_context():
        existing = User.query.filter_by(email=email).first()
        if existing:
            db.session.delete(existing)
        user = User(email=email, password=password, role=RoleType.USER)
        db.session.add(user)
        db.session.commit()
        profile = UserProfile(
            user_id=user.id,
            name="Recovery",
            surname="User",
            affiliation="Locust Tests",
            orcid="0000-0000-0000-0000",
            enabled_two_factor=False,
        )
        db.session.add(profile)
        db.session.commit()
    return email, password


def delete_recovery_user(email: str) -> None:
    with flask_app.app_context():
        user = User.query.filter_by(email=email).first()
        if user:
            if user.profile:
                db.session.delete(user.profile)
            db.session.delete(user)
            db.session.commit()


def fetch_reset_token(email: str) -> str | None:
    with flask_app.app_context():
        user = User.query.filter_by(email=email).first()
        return user.reset_token if user else None


class PasswordRecoveryBehavior(TaskSet):
    def on_start(self):
        self.ensure_logged_out()
        self.email, self.password = create_recovery_user()

    def on_stop(self):
        self.ensure_logged_out()
        delete_recovery_user(self.email)

    def ensure_logged_out(self):
        self.client.get("/logout")

    @task
    def forgot_password_and_reset(self):
        self.ensure_logged_out()

        response = self.client.get("/forgot-password")
        if response.status_code != 200:
            response.failure(f"Forgot password page unavailable: {response.status_code}")
            return

        try:
            csrf_token = get_csrf_token(response)
        except ValueError as exc:
            response.failure(f"Missing CSRF token: {exc}")
            return

        with silent_mail():
            reset_response = self.client.post(
                "/forgot-password",
                data={"email": self.email, "csrf_token": csrf_token},
            )

        if reset_response.status_code != 200 or "Correo de recuperación enviado" not in reset_response.text:
            reset_response.failure("Forgot password submission failed")
            return

        token = fetch_reset_token(self.email)
        if not token:
            reset_response.failure("Reset token missing in DB")
            return

        reset_page = self.client.get(f"/reset-password/{token}")
        if reset_page.status_code != 200:
            reset_page.failure("Reset page inaccessible")
            return

        try:
            csrf_token = get_csrf_token(reset_page)
        except ValueError as exc:
            reset_page.failure(f"Reset CSRF token missing: {exc}")
            return

        self.password = f"New{uuid4().hex[:6]}Pass!"

        reset_post = self.client.post(
            f"/reset-password/{token}",
            data={"password": self.password, "csrf_token": csrf_token},
            allow_redirects=False,
        )
        if reset_post.status_code not in (200, 302):
            reset_post.failure("Password reset submission failed")
            return

        login_page = self.client.get("/login")
        try:
            csrf_token = get_csrf_token(login_page)
        except ValueError:
            login_page.failure("Login CSRF token missing after reset")
            return

        login_response = self.client.post(
            "/login",
            data={"email": self.email, "password": self.password, "csrf_token": csrf_token},
            allow_redirects=False,
        )
        if login_response.status_code not in (200, 302):
            login_response.failure("Login with reset password failed")
        self.ensure_logged_out()


class AuthUser(HttpUser):
    tasks = [SignupBehavior, LoginBehavior, TwoFactorLoginBehavior, PasswordRecoveryBehavior]
    min_wait = 5000
    max_wait = 9000
    host = get_host_for_locust_testing()
