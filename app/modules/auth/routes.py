from datetime import datetime

from flask import redirect, render_template, request, url_for
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
    if request.method == "POST" and form.validate_on_submit():
        if authentication_service.login(form.email.data, form.password.data):
            return redirect(url_for("public.index"))

        return render_template("auth/login_form.html", form=form, error="Invalid credentials")

    return render_template("auth/login_form.html", form=form)


@auth_bp.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("public.index"))


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
