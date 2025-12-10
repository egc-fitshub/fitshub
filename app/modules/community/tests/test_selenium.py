import time
import pytest
import time
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

from selenium.common.exceptions import NoSuchElementException

from core.environment.host import get_host_for_selenium_testing
from core.selenium.common import close_driver, initialize_driver


def test_community_index():
    driver = initialize_driver()

    try:
        host = get_host_for_selenium_testing()

        # Open the index page
        driver.get(f"{host}/community")


        # Wait a little while to make sure the page has loaded completely
        time.sleep(4)

        try:
            driver.find_element(By.CSS_SELECTOR, ".nav-link:nth-child(1)").click()
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


# Call the test function
test_community_index()

    
 
   
  