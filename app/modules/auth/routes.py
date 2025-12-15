import base64
import io
from datetime import datetime

import pyotp
import qrcode
from flask import redirect, render_template, request, session, url_for
from flask_login import current_user, login_required, login_user, logout_user
from werkzeug.security import generate_password_hash

from app import db
from app.modules.auth import auth_bp
from app.modules.auth.forms import ForgotPasswordForm, LoginForm, ResetPasswordForm, SignupForm
from app.modules.auth.models import User
from app.modules.auth.services import AuthenticationService
from app.modules.profile.services import UserProfileService

authentication_service = AuthenticationService()
user_profile_service = UserProfileService()


@auth_bp.route("/signup/", methods=["GET", "POST"])
def show_signup_form():
    if current_user.is_authenticated:
        return redirect(url_for("public.index"))

    form = SignupForm()
    if form.validate_on_submit():
        email = form.email.data
        if not authentication_service.is_email_available(email):
            return render_template("auth/signup_form.html", form=form, error=f"Email {email} in use")

        try:
            user = authentication_service.create_with_profile(**form.data)
        except Exception as exc:
            return render_template("auth/signup_form.html", form=form, error=f"Error creating user: {exc}")

        # Log user
        login_user(user, remember=True)
        return redirect(url_for("public.index"))

    return render_template("auth/signup_form.html", form=form)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("public.index"))

    form = LoginForm()
    qr_code_data = None
    needs_2fa = False

    if request.method == "POST":
        if "pending_user_id" in session:
            user = User.query.get(session["pending_user_id"])

            if not user:
                session.pop("pending_user_id", None)
                session.pop("remember_me", None)
                session.pop("temp_token", None)
                return render_template("auth/login_form.html", form=form, error="Session expired. Please login again.")

            code = form.code.data

            if not code or len(code) != 6:
                needs_2fa = True
                if user.token is None and "temp_token" in session:
                    token = session["temp_token"]
                    totp_uri = pyotp.TOTP(token).provisioning_uri(
                        name=f"{user.profile.surname}, {user.profile.name}", issuer_name="FITSHUB.IO"
                    )
                    qr_image = qrcode.make(totp_uri).get_image()
                    buffered = io.BytesIO()
                    qr_image.save(buffered, format="PNG")
                    qr_code_data = base64.b64encode(buffered.getvalue()).decode()

                return render_template(
                    "auth/login_form.html",
                    form=form,
                    qr_code=qr_code_data,
                    needs_2fa=needs_2fa,
                    error="Please enter a valid 6-digit code.",
                )

            if user.token is None:
                temp_token = session.get("temp_token")
                if not temp_token:
                    session.pop("pending_user_id", None)
                    session.pop("remember_me", None)
                    return render_template(
                        "auth/login_form.html", form=form, error="Session expired. Please try again."
                    )

                try:
                    authentication_service.set_user_token(user, temp_token, code)
                    login_user(user, remember=session.get("remember_me", False))
                    session.pop("pending_user_id", None)
                    session.pop("remember_me", None)
                    session.pop("temp_token", None)
                    return redirect(url_for("public.index"))
                except ValueError:
                    totp_uri = pyotp.TOTP(temp_token).provisioning_uri(
                        name=f"{user.profile.surname}, {user.profile.name}", issuer_name="FITSHUB.IO"
                    )
                    qr_image = qrcode.make(totp_uri).get_image()
                    buffered = io.BytesIO()
                    qr_image.save(buffered, format="PNG")
                    qr_code_data = base64.b64encode(buffered.getvalue()).decode()
                    needs_2fa = True
                    return render_template(
                        "auth/login_form.html",
                        form=form,
                        qr_code=qr_code_data,
                        needs_2fa=needs_2fa,
                        error="Invalid authentication code. Please try again.",
                    )
            else:
                if authentication_service.verify_token(user, code):
                    login_user(user, remember=session.get("remember_me", False))
                    session.pop("pending_user_id", None)
                    session.pop("remember_me", None)
                    return redirect(url_for("public.index"))
                else:
                    needs_2fa = True
                    return render_template(
                        "auth/login_form.html",
                        form=form,
                        needs_2fa=needs_2fa,
                        error="Invalid authentication code. Please try again.",
                    )

        else:
            email = form.email.data
            password = form.password.data

            if not email or not password:
                return render_template("auth/login_form.html", form=form, error="Email and password are required.")

            user = authentication_service.repository.get_by_email(email)

            if user is None or not user.check_password(password):
                return render_template("auth/login_form.html", form=form, error="Invalid credentials")

            if user.profile is None or not user.profile.enabled_two_factor:
                login_user(user, remember=form.remember_me.data)
                return redirect(url_for("public.index"))

            session["pending_user_id"] = user.id
            session["remember_me"] = form.remember_me.data

            needs_2fa = True

            if user.token is None:
                qr_image, token = authentication_service.generate_qr_code(user)
                session["temp_token"] = token

                buffered = io.BytesIO()
                qr_image.save(buffered, format="PNG")
                qr_code_data = base64.b64encode(buffered.getvalue()).decode()

            return render_template("auth/login_form.html", form=form, qr_code=qr_code_data, needs_2fa=needs_2fa)

    if "pending_user_id" in session:
        user = User.query.get(session["pending_user_id"])
        if user:
            needs_2fa = True
            if user.token is None and "temp_token" in session:
                token = session["temp_token"]
                totp_uri = pyotp.TOTP(token).provisioning_uri(
                    name=f"{user.profile.surname}, {user.profile.name}", issuer_name="FITSHUB.IO"
                )
                qr_image = qrcode.make(totp_uri).get_image()
                buffered = io.BytesIO()
                qr_image.save(buffered, format="PNG")
                qr_code_data = base64.b64encode(buffered.getvalue()).decode()
        else:
            session.pop("pending_user_id", None)
            session.pop("remember_me", None)
            session.pop("temp_token", None)

    return render_template("auth/login_form.html", form=form, qr_code=qr_code_data, needs_2fa=needs_2fa)


@auth_bp.route("/logout")
def logout():
    logout_user()
    session.pop("pending_user_id", None)
    session.pop("remember_me", None)
    session.pop("temp_token", None)
    return redirect(url_for("public.index"))


@auth_bp.route("/admin_roles", methods=["GET"])
@login_required
def admin_roles():
    if current_user.role.value != "administrator":
        return redirect(url_for("public.index"))
    roles = authentication_service.get_users_roles()
    return render_template("auth/admin_roles.html", roles=roles)


@auth_bp.route("/update_roles", methods=["POST"])
@login_required
def update_roles():
    if current_user.role.value != "administrator":
        return redirect(url_for("public.index"))

    updates = []
    for key, value in request.form.items():
        if key.startswith("role_"):
            user_id = key.split("_")[1]
            new_role = value
            updates.append((user_id, new_role))

    for user_id, new_role in updates:
        try:
            authentication_service.update_user_role(user_id, new_role)
        except Exception:
            return redirect(url_for("public.index"))

    return redirect(url_for("auth.admin_roles"))


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password_view():
    form = ForgotPasswordForm()
    if request.method == "POST":
        email = request.form.get("email")
        user = User.query.filter_by(email=email).first()
        if not user:
            return render_template("auth/forgot_password.html", form=form, error="Correo no registrado.")
        authentication_service.send_password_reset_email(user)
        return render_template("auth/forgot_password.html", form=form, message="Correo de recuperación enviado.")
    return render_template("auth/forgot_password.html", form=form)


@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password_view(token):
    form = ResetPasswordForm()
    user = User.query.filter_by(reset_token=token).first()
    if not user or user.token_expiration < datetime.utcnow():
        return render_template("reset_password.html", error="Token inválido o expirado.")

    if request.method == "POST":
        new_password = request.form.get("password")
        user.password = generate_password_hash(new_password)
        user.reset_token = None
        user.token_expiration = None
        db.session.commit()
        return redirect(url_for("auth.login"))

    return render_template("auth/reset_password.html", form=form)
