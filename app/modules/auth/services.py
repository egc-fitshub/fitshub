import os
import secrets
from datetime import datetime, timedelta

from flask import url_for
from flask_login import current_user, login_user
from flask_mail import Message

from app import db, mail
from app.modules.auth.models import User
from app.modules.auth.repositories import UserRepository
from app.modules.profile.models import UserProfile
from app.modules.profile.repositories import UserProfileRepository
from core.configuration.configuration import uploads_folder_name
from core.services.BaseService import BaseService
import pyotp
import qrcode

from .models import RoleType


class AuthenticationService(BaseService):
    def __init__(self):
        super().__init__(UserRepository())
        self.user_profile_repository = UserProfileRepository()

    def login(self, email, password, remember=True):
        user = self.repository.get_by_email(email)
        if user is not None and user.check_password(password):
            login_user(user, remember=remember)
            return True
        return False

    def is_email_available(self, email: str) -> bool:
        return self.repository.get_by_email(email) is None

    def create_with_profile(self, **kwargs):
        try:
            email = kwargs.pop("email", None)
            password = kwargs.pop("password", None)
            name = kwargs.pop("name", None)
            surname = kwargs.pop("surname", None)

            if not email:
                raise ValueError("Email is required.")
            if not password:
                raise ValueError("Password is required.")
            if not name:
                raise ValueError("Name is required.")
            if not surname:
                raise ValueError("Surname is required.")

            user_data = {"email": email, "password": password}

            profile_data = {
                "name": name,
                "surname": surname,
            }

            user = self.create(commit=False, **user_data)
            profile_data["user_id"] = user.id
            self.user_profile_repository.create(**profile_data)
            self.repository.session.commit()
        except Exception as exc:
            self.repository.session.rollback()
            raise exc
        return user

    def update_profile(self, user_profile_id, form):
        if form.validate():
            updated_instance = self.update(user_profile_id, **form.data)
            return updated_instance, None

        return None, form.errors

    def get_authenticated_user(self) -> User | None:
        if current_user.is_authenticated:
            return current_user
        return None

    def get_authenticated_user_profile(self) -> UserProfile | None:
        if current_user.is_authenticated:
            return current_user.profile
        return None

    def temp_folder_by_user(self, user: User) -> str:
        return os.path.join(uploads_folder_name(), "temp", str(user.id))

    def send_password_reset_email(self, user):
        token = secrets.token_urlsafe(32)
        user.reset_token = token
        user.token_expiration = datetime.utcnow() + timedelta(hours=1)
        db.session.commit()

        reset_url = url_for("auth.reset_password_view", token=token, _external=True)

        msg = Message(
            subject="Recuperación de contraseña - Fitshub",
            recipients=[user.email],
            body=(
                f"Hola,\n\n"
                f"Has solicitado restablecer tu contraseña en Fitshub.\n\n"
                f"Para hacerlo, haz clic en el siguiente enlace:\n{reset_url}\n\n"
                f"Este enlace expirará en 1 hora.\n\n"
                "Si no solicitaste este cambio, puedes ignorar este mensaje.\n\n"
                "-- Equipo Fitshub"
            ),
        )

        mail.send(msg)

    def get_users_roles(self):
        if current_user.role != RoleType.ADMINISTRATOR:
            raise PermissionError("Se requiere rol de administrador para esta acción.")
        return self.repository.get_roles()

    def get_curators(self):
        return self.repository.get_curators()

    def update_user_role(self, user_id, new_role):
        if new_role not in ["administrator", "curator", "user"]:
            raise ValueError(f"Invalid role '{new_role}'")

        if new_role == "administrator":
            role_to_set = RoleType.ADMINISTRATOR
        elif new_role == "curator":
            role_to_set = RoleType.CURATOR
        else:
            role_to_set = RoleType.USER

        try:
            self.update(user_id, role=role_to_set)
        except Exception as e:
            self.repository.session.rollback()
            raise e

    def get_curated_communities_by_id(self, user_id):
        user = self.repository.get_or_404(user_id)
        if user.curated_communities:
            return user.curated_communities
        else:
            return None

    def get_curated_communities_by_id(self, user_id):
        user = self.repository.get_or_404(user_id)
        if user.curated_communities:
            return user.curated_communities
        else:
            return None

    def set_user_token(self, user: User, token: str, code: str) -> None:
        totp = pyotp.TOTP(token)
        if not totp.verify(code):
            raise ValueError("Invalid authentication code.")
        user.token = token
        db.session.commit()

    def generate_qr_code(self, user: User) -> (tuple):
        token = pyotp.random_base32()
        totp = pyotp.TOTP(token).provisioning_uri(name=f"{user.profile.surname}, {user.profile.name}", issuer_name="FITSHUB.IO")
        return (qrcode.make(totp).get_image(), token)

    def verify_token(self, user: User, code: str) -> bool:
        totp = pyotp.TOTP(user.token)
        return totp.verify(code)