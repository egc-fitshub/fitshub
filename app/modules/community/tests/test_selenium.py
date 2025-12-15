import time

from selenium.common.exceptions import NoAlertPresentException, NoSuchElementException
from selenium.webdriver.common.by import By

from core.environment.host import get_host_for_selenium_testing
from core.selenium.common import close_driver, initialize_driver


def test_community_index():
    driver = initialize_driver()

    try:
        host = get_host_for_selenium_testing()

        # Open the index page
        driver.get(f"{host}/login")

        # Wait a little while to make sure the page has loaded completely
        time.sleep(4)

        try:
            driver.find_element(By.ID, "email").click()
            driver.find_element(By.ID, "email").send_keys("admin@example.com")
            driver.find_element(By.ID, "password").click()
            driver.find_element(By.ID, "password").send_keys("1234")
            driver.find_element(By.ID, "submit").click()
            driver.find_element(By.LINK_TEXT, "My communities").click()
            driver.find_element(By.LINK_TEXT, "Test community 2").click()
            driver.find_element(By.LINK_TEXT, "Edit Community Details").click()
            driver.find_element(By.ID, "description").click()
            driver.find_element(By.ID, "description").send_keys("This is a test description for selenium")
            driver.find_element(By.ID, "submit").click()
            driver.find_element(By.LINK_TEXT, "Create a community").click()
            driver.find_element(By.CSS_SELECTOR, ".active .align-middle:nth-child(2)").click()
            driver.find_element(By.CSS_SELECTOR, ".sidebar-item:nth-child(2) .align-middle:nth-child(2)").click()
            driver.find_element(By.CSS_SELECTOR, ".content").click()
        except NoSuchElementException:
            raise AssertionError("Test failed!")

    finally:
        # Close the browser
        close_driver(driver)


def test_create_community():
    driver = initialize_driver()

    try:
        host = get_host_for_selenium_testing()

        # Open the index page
        driver.get(f"{host}/login")

        # Wait a little while to make sure the page has loaded completely
        time.sleep(4)

        try:
            driver.find_element(By.ID, "email").click()
            driver.find_element(By.ID, "email").send_keys("admin@example.com")
            driver.find_element(By.ID, "password").click()
            driver.find_element(By.ID, "password").send_keys("1234")
            driver.find_element(By.ID, "submit").click()
            driver.find_element(By.LINK_TEXT, "Create a community").click()
            driver.find_element(By.ID, "name").click()
            driver.find_element(By.ID, "name").send_keys("Create")
            driver.find_element(By.ID, "description").click()
            driver.find_element(By.ID, "description").send_keys("This is a test")
            driver.find_element(By.ID, "submit").click()
        except NoSuchElementException:
            raise AssertionError("Test failed!")

    finally:
        # Close the browser
        close_driver(driver)


def test_edit_community():
    driver = initialize_driver()

    try:
        host = get_host_for_selenium_testing()

        # Open the index page
        driver.get(f"{host}/login")

        # Wait a little while to make sure the page has loaded completely
        time.sleep(4)

        try:
            driver.find_element(By.ID, "email").click()
            driver.find_element(By.ID, "email").send_keys("admin@example.com")
            driver.find_element(By.ID, "password").click()
            driver.find_element(By.ID, "password").send_keys("1234")
            driver.find_element(By.ID, "submit").click()
            driver.find_element(By.LINK_TEXT, "My communities").click()
            driver.find_element(By.LINK_TEXT, "Create").click()
            driver.find_element(By.LINK_TEXT, "Edit Community Details").click()
            driver.find_element(By.ID, "description").click()
            driver.find_element(By.ID, "description").send_keys("Test edition")
            driver.find_element(By.ID, "submit").click()
        except NoSuchElementException:
            raise AssertionError("Test failed!")

    finally:
        # Close the browser
        close_driver(driver)


def test_delete_community():
    driver = initialize_driver()

    try:
        host = get_host_for_selenium_testing()

        # Open the index page
        driver.get(f"{host}/login")

        # Wait a little while to make sure the page has loaded completely
        time.sleep(4)

        try:
            driver.find_element(By.ID, "email").click()
            driver.find_element(By.ID, "email").send_keys("admin@example.com")
            driver.find_element(By.ID, "password").click()
            driver.find_element(By.ID, "password").send_keys("1234")
            driver.find_element(By.ID, "submit").click()
            driver.find_element(By.LINK_TEXT, "My communities").click()
            driver.find_element(By.LINK_TEXT, "Create").click()
            driver.find_element(By.CSS_SELECTOR, ".btn-outline-danger").click()
            assert (
                driver.switch_to.alert.text
                == "Are you sure you want to delete this community? This action cannot be undone."
            )
            driver.switch_to.alert.accept()
            time.sleep(2)
        except NoSuchElementException as e:
            raise AssertionError(f"Test failed! Element not found: {e}")

        except NoAlertPresentException:
            raise AssertionError("Test failed! JavaScript confirmation dialog did not appear.")

    finally:
        # Close the browser
        close_driver(driver)
