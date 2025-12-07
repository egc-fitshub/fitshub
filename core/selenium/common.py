import os

from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from webdriver_manager.firefox import GeckoDriverManager


def initialize_driver():
    options = webdriver.FirefoxOptions()

    firefox_path = os.environ.get("FIREFOX_BINARY", "/Applications/Firefox.app/Contents/MacOS/firefox")
    if os.path.exists(firefox_path):
        options.binary_location = firefox_path

    snap_tmp = os.path.expanduser("~/snap/firefox/common/tmp")
    os.makedirs(snap_tmp, exist_ok=True)
    os.environ["TMPDIR"] = snap_tmp

    driver_binary = os.environ.get("GECKODRIVER", "/opt/homebrew/bin/geckodriver")
    service = Service(driver_binary)
    driver = webdriver.Firefox(service=service, options=options)
    return driver


def close_driver(driver):
    driver.quit()
