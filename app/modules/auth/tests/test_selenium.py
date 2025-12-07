import pyotp
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from core.environment.host import get_host_for_selenium_testing
from core.selenium.common import close_driver, initialize_driver
from app import app as flask_app, db
from app.modules.auth.models import RoleType, User
from app.modules.profile.models import UserProfile


TWO_FACTOR_EMAIL = "twofactor@example.com"
TWO_FACTOR_PASSWORD = "test1234"
TWO_FACTOR_SECRET = "JBSWY3DPEHPK3PXP"


def wait_for_page_to_load(driver, timeout=8):
    WebDriverWait(driver, timeout).until(
        lambda driver: driver.execute_script("return document.readyState") == "complete"
    )


def wait_for_element(driver, locator, timeout=10):
    return WebDriverWait(driver, timeout).until(EC.visibility_of_element_located(locator))


def ensure_two_factor_user():
    with flask_app.app_context():
        user = User.query.filter_by(email=TWO_FACTOR_EMAIL).first()
        if not user:
            user = User(email=TWO_FACTOR_EMAIL, password=TWO_FACTOR_PASSWORD, role=RoleType.USER, token=TWO_FACTOR_SECRET)
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
            wait_for_element(
                driver, (By.XPATH, "//h1[contains(@class, 'h2 mb-3') and contains(., 'Latest datasets')]")
            )
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

        wait_for_element(
            driver, (By.XPATH, "//h1[contains(@class, 'h2 mb-3') and contains(., 'Latest datasets')]")
        )
        assert driver.current_url != f"{host}/login"

        driver.get(f"{host}/logout")
        wait_for_page_to_load(driver)
        driver.get(f"{host}/admin_roles")
        wait_for_page_to_load(driver)
        wait_for_element(driver, (By.XPATH, "//h1[contains(@class, 'h2 mb-3') and contains(., 'Login')]"))
        print("2FA login test passed!")

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


# Call the test functions
test_login_and_check_element()
test_two_factor_login_flow()
test_two_factor_invalid_code_shows_error()
