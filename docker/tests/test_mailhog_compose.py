import os
import smtplib
import subprocess
import time
from typing import Optional

import requests

COMPOSE_FILE = os.path.join(os.path.dirname(__file__), "..", "docker-compose.dev.yml")


def send_email(host: str, port: int, sender: str, recipients: list[str], subject: str, body: str) -> None:
    msg = (
        f"Subject: {subject}\r\n"
        f"From: {sender}\r\n"
        f"To: {', '.join(recipients)}\r\n"
        "\r\n"
        f"{body}"
    )
    with smtplib.SMTP(host, port, timeout=5) as s:
        s.sendmail(sender, recipients, msg)


def find_message(api_url: str, subject: str, timeout: float = 10.0, poll_interval: float = 0.5) -> Optional[dict]:
    api_base = api_url.rstrip("/")
    end = time.time() + timeout
    while time.time() < end:
        r = requests.get(f"{api_base}/api/v2/messages", timeout=5)
        data = r.json()
        for item in data.get("items", []):
            headers = item.get("Content", {}).get("Headers", {})
            subj_list = headers.get("Subject", [])
            for s in subj_list:
                if subject in s:
                    return item
        time.sleep(poll_interval)
    return None


def test_mailhog_via_compose(mailhog_compose):

    subject = "Test-mailhog-test_mailhog_via_compose"

    send_email(mailhog_compose["smtp_host"], mailhog_compose["smtp_port"],
               "from@test", ["to@test.com"], subject, "body")

    found = find_message(mailhog_compose["api"], subject)
    assert found is not None, "Message did not appear in MailHog API"


def test_web_sends_mail(mailhog_compose):
    subject = "Test-from-web-container-test_web_sends_mail"

    python_code = (
        "from app import create_app, mail\n"
        "from flask_mail import Message\n"
        "app = create_app()\n"
        "with app.app_context():\n"
        "    m = Message(subject=%r, recipients=['to@test.com'], body='body')\n"
        "    mail.send(m)\n"
    ) % subject

    cmd = [
        "docker", "compose", "-f", COMPOSE_FILE, "exec", "-T", "web",
        "python", "-c", python_code,
    ]
    subprocess.run(cmd, check=True)

    found = find_message(mailhog_compose["api"], subject)
    assert found is not None, "Message sent from web container did not appear in MailHog API"
