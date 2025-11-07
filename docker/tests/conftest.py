import os
import socket
import subprocess
import time
from typing import Dict

import pytest
import requests

COMPOSE_FILE = os.path.join(os.path.dirname(__file__), "..", "docker-compose.dev.yml")
COMPOSE_FILE = os.path.abspath(COMPOSE_FILE)


def _wait_for_mailhog(host: str, smtp_port: int, api_url: str, timeout: float = 15.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            # check SMTP socket
            with socket.create_connection((host, smtp_port), timeout=1):
                pass

            # check HTTP API
            r = requests.get(f"{api_url}/api/v2/messages", timeout=1)
            if r.status_code == 200:
                return True
        except Exception:
            time.sleep(0.2)
    return False


def _wait_for_web(timeout: float = 20.0) -> bool:
    web_ready_deadline = time.time() + timeout
    while time.time() < web_ready_deadline:
        try:
            proc = subprocess.run(
                ["docker", "compose", "-f", COMPOSE_FILE, "exec", "-T", "web",
                 "python", "-c", "import sys; sys.exit(0)"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            if proc.returncode == 0:
                return True
        except Exception:
            # Retry
            pass
        time.sleep(0.5)
    return False


@pytest.fixture(scope="session")
def mailhog_compose() -> Dict[str, str]:
    try:
        subprocess.run(["docker", "compose", "-f", COMPOSE_FILE, "up", "-d", "web", "mailhog"], check=True)
    except subprocess.CalledProcessError as e:
        pytest.skip(f"Failed to start mailhog or web compose service: {e}")

    host = "localhost"
    smtp_port = 1025
    api_url = "http://localhost:8025"

    try:
        ready = _wait_for_mailhog(host, smtp_port, api_url, timeout=15.0)
        if not ready:
            raise RuntimeError("MailHog did not become ready in time")

        if not _wait_for_web(timeout=20.0):
            raise RuntimeError("web service did not become ready in time")

        yield {"smtp_host": host, "smtp_port": smtp_port, "api": api_url}
    finally:
        subprocess.run(["docker", "compose", "-f", COMPOSE_FILE, "down", "-v"], check=True)
