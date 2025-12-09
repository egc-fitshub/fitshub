import os
import time

import pytest
import requests
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from core.environment.host import get_host_for_selenium_testing
from core.selenium.common import close_driver, initialize_driver


def test_login_and_check_element():
    driver = initialize_driver()

    try:
        host = get_host_for_selenium_testing()

        # Open the login page
        driver.get(f"{host}/login")

        # Wait a little while to make sure the page has loaded completely
        time.sleep(4)

        # Find the username and password field and enter the values
        email_field = driver.find_element(By.NAME, "email")
        password_field = driver.find_element(By.NAME, "password")

        email_field.send_keys("user1@example.com")
        password_field.send_keys("1234")

        # Send the form
        password_field.send_keys(Keys.RETURN)

        # Wait a little while to ensure that the action has been completed
        time.sleep(4)

        try:
            driver.find_element(By.XPATH, "//h1[contains(@class, 'h2 mb-3') and contains(., 'Latest datasets')]")
            print("Test passed!")

        except NoSuchElementException:
            raise AssertionError("Test failed!")

    finally:
        # Close the browser
        close_driver(driver)


def test_connect_to_mailhog():
    """Test connection to MailHog web interface.
    Runs only in Docker environment where MailHog is reachable.
    """
    if not (os.getenv("WORKING_DIR") == "/app/"):
        pytest.skip("Only runs in Docker environment")

    driver = initialize_driver()

    try:
        host = "mailhog" if os.getenv("WORKING_DIR") == "/app/" else "localhost"
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


def test_forgot_password_mailhog():
    """
    Submit the forgot-password form and verify MailHog received the email.
    Runs only in the Docker environment where MailHog is reachable.
    """
    if not (os.getenv("WORKING_DIR") == "/app/"):
        pytest.skip("Only runs in Docker environment")

    target_email = "user1@example.com"

    driver = initialize_driver()
    try:
        host = get_host_for_selenium_testing()

        # Open the forgot password page and submit the form
        driver.get(f"{host}/forgot-password")
        time.sleep(2)

        email_field = driver.find_element(By.NAME, "email")
        email_field.clear()
        email_field.send_keys(target_email)
        email_field.send_keys(Keys.RETURN)

        time.sleep(2)

    finally:
        close_driver(driver)

    # Poll MailHog API for the message (up to 20s)
    mailhog_host = "mailhog" if os.getenv("WORKING_DIR") == "/app/" else "localhost"
    api_url = f"http://{mailhog_host}:8025/api/v2/messages"

    found = False
    deadline = time.time() + 20
    while time.time() < deadline:
        resp = requests.get(api_url, timeout=5)
        resp.raise_for_status()
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
