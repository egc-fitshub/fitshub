import secrets
from datetime import datetime, timedelta, timezone
from flask_mail import Message
from flask import url_for
from app import mail, db


def send_password_reset_email(user):
    # Genera un token y envia un correo de recuperación de contraseña
    token = secrets.token_urlsafe(32)
    user.reset_token = token
    user.token_expiration = datetime.now(timezone.utc) + timedelta(hours=1)
    db.session.commit()

    reset_url = url_for('auth.reset_password', token=token, _external=True)

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
