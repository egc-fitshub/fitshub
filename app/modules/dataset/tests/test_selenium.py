import os
import time

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait

from core.environment.host import get_host_for_selenium_testing
from core.selenium.common import close_driver, initialize_driver


def wait_for_page_to_load(driver, timeout=4):
    WebDriverWait(driver, timeout).until(
        lambda driver: driver.execute_script("return document.readyState") == "complete"
    )


def count_datasets(driver, host):
    driver.get(f"{host}/dataset/list")
    wait_for_page_to_load(driver)

    try:
        amount_datasets = len(driver.find_elements(By.XPATH, "//table//tbody//tr"))
    except Exception:
        amount_datasets = 0
    return amount_datasets


def count_home_datasets(driver, host):
    driver.get(f"{host}/")
    wait_for_page_to_load(driver)

    try:
        amount_datasets = len(driver.find_elements(By.ID, "dataset_card"))
    except Exception:
        amount_datasets = 0
    return amount_datasets


def count_trending_datasets(driver, host):
    driver.get(f"{host}/")
    wait_for_page_to_load(driver)

    try:
        amount_datasets = len(driver.find_elements(By.ID, "trending_dataset"))
    except Exception:
        amount_datasets = 0
    return amount_datasets


def test_upload_dataset():
    driver = initialize_driver()

    try:
        host = get_host_for_selenium_testing()

        # Open the login page
        driver.get(f"{host}/login")
        wait_for_page_to_load(driver)

        # Find the username and password field and enter the values
        email_field = driver.find_element(By.NAME, "email")
        password_field = driver.find_element(By.NAME, "password")

        email_field.send_keys("user1@example.com")
        password_field.send_keys("1234")

        # Send the form
        password_field.send_keys(Keys.RETURN)
        time.sleep(4)
        wait_for_page_to_load(driver)

        # Count initial datasets
        initial_datasets = count_datasets(driver, host)

        # Open the upload dataset
        driver.get(f"{host}/dataset/upload")
        wait_for_page_to_load(driver)

        # Find basic info and FITS model and fill values
        title_field = driver.find_element(By.NAME, "title")
        title_field.send_keys("Title")
        desc_field = driver.find_element(By.NAME, "desc")
        desc_field.send_keys("Description")
        tags_field = driver.find_element(By.NAME, "tags")
        tags_field.send_keys("tag1,tag2")

        # Add two authors and fill
        add_author_button = driver.find_element(By.ID, "add_author")
        add_author_button.send_keys(Keys.RETURN)
        wait_for_page_to_load(driver)
        add_author_button.send_keys(Keys.RETURN)
        wait_for_page_to_load(driver)

        name_field0 = driver.find_element(By.NAME, "authors-0-name")
        name_field0.send_keys("Author0")
        affiliation_field0 = driver.find_element(By.NAME, "authors-0-affiliation")
        affiliation_field0.send_keys("Club0")
        orcid_field0 = driver.find_element(By.NAME, "authors-0-orcid")
        orcid_field0.send_keys("0000-0000-0000-0000")

        name_field1 = driver.find_element(By.NAME, "authors-1-name")
        name_field1.send_keys("Author1")
        affiliation_field1 = driver.find_element(By.NAME, "authors-1-affiliation")
        affiliation_field1.send_keys("Club1")

        # Obtén las rutas absolutas de los archivos
        file1_path = os.path.abspath("app/modules/dataset/fits_examples/file1.fits")
        file2_path = os.path.abspath("app/modules/dataset/fits_examples/file2.fits")

        # Subir el primer archivo
        dropzone = driver.find_element(By.CLASS_NAME, "dz-hidden-input")
        dropzone.send_keys(file1_path)
        wait_for_page_to_load(driver)

        # Subir el segundo archivo
        dropzone = driver.find_element(By.CLASS_NAME, "dz-hidden-input")
        dropzone.send_keys(file2_path)
        wait_for_page_to_load(driver)

        # Add authors in FITS models
        show_button = driver.find_element(By.ID, "0_button")
        show_button.send_keys(Keys.RETURN)
        add_author_fits_button = driver.find_element(By.ID, "0_form_authors_button")
        add_author_fits_button.send_keys(Keys.RETURN)
        wait_for_page_to_load(driver)

        name_field = driver.find_element(By.NAME, "fits_models-0-authors-2-name")
        name_field.send_keys("Author3")
        affiliation_field = driver.find_element(By.NAME, "fits_models-0-authors-2-affiliation")
        affiliation_field.send_keys("Club3")

        # Check I agree and send form
        check = driver.find_element(By.ID, "agreeCheckbox")
        check.send_keys(Keys.SPACE)
        wait_for_page_to_load(driver)

        upload_btn = driver.find_element(By.ID, "upload_button")
        upload_btn.send_keys(Keys.RETURN)
        wait_for_page_to_load(driver)
        time.sleep(2)  # Force wait time

        assert driver.current_url == f"{host}/dataset/list", "Test failed!"

        # Count final datasets
        final_datasets = count_datasets(driver, host)
        assert final_datasets == initial_datasets + 1, "Test failed!"

        print("Test upload dataset passed!")

    finally:
        # Close the browser
        close_driver(driver)
        
def test_upload_one_zip_dataset():
    driver = initialize_driver()
    try:
        host = get_host_for_selenium_testing()

        # Login
        driver.get(f"{host}/login")
        wait_for_page_to_load(driver)
        driver.find_element(By.NAME, "email").send_keys("user1@example.com")
        driver.find_element(By.NAME, "password").send_keys("1234")
        driver.find_element(By.NAME, "password").send_keys(Keys.RETURN)
        time.sleep(3)
        wait_for_page_to_load(driver)

        # Count initial datasets
        initial_datasets = count_datasets(driver, host)

        # Open upload page and fill basic info
        driver.get(f"{host}/dataset/upload")
        wait_for_page_to_load(driver)
        driver.find_element(By.NAME, "title").send_keys("Zip Upload Title")
        driver.find_element(By.NAME, "desc").send_keys("Zip upload description")
        driver.find_element(By.NAME, "tags").send_keys("zip,test")

        # Switch upload source to ZIP
        driver.execute_script(
            "const e = document.getElementById('upload-source'); e.value = 'zip'; e.dispatchEvent(new Event('change'));"
        )
        time.sleep(1)
        wait_for_page_to_load(driver)

        # Upload the zip using the hidden dropzone input
        zip_path = os.path.abspath("app/modules/dataset/zip_examples/one_fits.zip")

        dropzone = driver.find_element(By.CLASS_NAME, "dz-hidden-input")
        dropzone.send_keys(zip_path)
        time.sleep(2)
        wait_for_page_to_load(driver)

        # Agree and submit
        check = driver.find_element(By.ID, "agreeCheckbox")
        check.send_keys(Keys.SPACE)
        wait_for_page_to_load(driver)
        upload_btn = driver.find_element(By.ID, "upload_button")
        upload_btn.send_keys(Keys.RETURN)
        time.sleep(2)
        wait_for_page_to_load(driver)

        # Verify redirect and dataset count increment
        assert driver.current_url == f"{host}/dataset/list", "Upload via ZIP did not redirect to dataset list"
        final_datasets = count_datasets(driver, host)
        assert final_datasets == initial_datasets + 1, "Dataset count did not increase after ZIP upload"

        print("Upload one ZIP dataset test passed!")

    finally:
        close_driver(driver)

def test_upload_multiple_zip_dataset():
    driver = initialize_driver()
    try:
        host = get_host_for_selenium_testing()

        # Login
        driver.get(f"{host}/login")
        wait_for_page_to_load(driver)
        driver.find_element(By.NAME, "email").send_keys("user1@example.com")
        driver.find_element(By.NAME, "password").send_keys("1234")
        driver.find_element(By.NAME, "password").send_keys(Keys.RETURN)
        time.sleep(3)
        wait_for_page_to_load(driver)

        # Count initial datasets
        initial_datasets = count_datasets(driver, host)

        # Open upload page and fill basic info
        driver.get(f"{host}/dataset/upload")
        wait_for_page_to_load(driver)
        driver.find_element(By.NAME, "title").send_keys("Zip Multiple Upload Title")
        driver.find_element(By.NAME, "desc").send_keys("Zip multiple upload description")
        driver.find_element(By.NAME, "tags").send_keys("zip,test")

        # Switch upload source to ZIP
        driver.execute_script(
            "const e = document.getElementById('upload-source'); e.value = 'zip'; e.dispatchEvent(new Event('change'));"
        )
        time.sleep(1)
        wait_for_page_to_load(driver)

        # Upload the zip using the hidden dropzone input
        zip_path = os.path.abspath("app/modules/dataset/zip_examples/multiple_fits.zip")

        dropzone = driver.find_element(By.CLASS_NAME, "dz-hidden-input")
        dropzone.send_keys(zip_path)
        time.sleep(2)
        wait_for_page_to_load(driver)

        # Agree and submit
        check = driver.find_element(By.ID, "agreeCheckbox")
        check.send_keys(Keys.SPACE)
        wait_for_page_to_load(driver)
        upload_btn = driver.find_element(By.ID, "upload_button")
        upload_btn.send_keys(Keys.RETURN)
        time.sleep(2)
        wait_for_page_to_load(driver)

        # Verify redirect and dataset count increment
        assert driver.current_url == f"{host}/dataset/list", "Upload via ZIP did not redirect to dataset list"
        final_datasets = count_datasets(driver, host)
        assert final_datasets == initial_datasets + 1, "Dataset count did not increase after ZIP upload"
        
        driver.find_element(By.LINK_TEXT, "Zip Multiple Upload Title").click()
        wait_for_page_to_load(driver)
        
        file_items = driver.find_elements(
            By.XPATH,
            "//div[contains(@class,'list-group')]/div[contains(@class,'list-group-item')][position()>1]"
        )
        assert len(file_items) == 2, f"Expected 2 files in dataset, found {len(file_items)}"

        print("Upload multiple ZIP datasets test passed!")

    finally:
        close_driver(driver)
        
def test_upload_folder_zip_dataset():
    driver = initialize_driver()
    try:
        host = get_host_for_selenium_testing()

        # Login
        driver.get(f"{host}/login")
        wait_for_page_to_load(driver)
        driver.find_element(By.NAME, "email").send_keys("user1@example.com")
        driver.find_element(By.NAME, "password").send_keys("1234")
        driver.find_element(By.NAME, "password").send_keys(Keys.RETURN)
        time.sleep(3)
        wait_for_page_to_load(driver)

        # Count initial datasets
        initial_datasets = count_datasets(driver, host)

        # Open upload page and fill basic info
        driver.get(f"{host}/dataset/upload")
        wait_for_page_to_load(driver)
        driver.find_element(By.NAME, "title").send_keys("Zip Folder Upload Title")
        driver.find_element(By.NAME, "desc").send_keys("Zip folder upload description")
        driver.find_element(By.NAME, "tags").send_keys("zip,test")

        # Switch upload source to ZIP
        driver.execute_script(
            "const e = document.getElementById('upload-source'); e.value = 'zip'; e.dispatchEvent(new Event('change'));"
        )
        time.sleep(1)
        wait_for_page_to_load(driver)

        # Upload the zip using the hidden dropzone input
        zip_path = os.path.abspath("app/modules/dataset/zip_examples/fits_in_folder.zip")

        dropzone = driver.find_element(By.CLASS_NAME, "dz-hidden-input")
        dropzone.send_keys(zip_path)
        time.sleep(2)
        wait_for_page_to_load(driver)

        # Agree and submit
        check = driver.find_element(By.ID, "agreeCheckbox")
        check.send_keys(Keys.SPACE)
        wait_for_page_to_load(driver)
        upload_btn = driver.find_element(By.ID, "upload_button")
        upload_btn.send_keys(Keys.RETURN)
        time.sleep(2)
        wait_for_page_to_load(driver)

        # Verify redirect and dataset count increment
        assert driver.current_url == f"{host}/dataset/list", "Upload via ZIP did not redirect to dataset list"
        final_datasets = count_datasets(driver, host)
        assert final_datasets == initial_datasets + 1, "Dataset count did not increase after ZIP upload"

        driver.find_element(By.LINK_TEXT, "Zip Folder Upload Title").click()
        wait_for_page_to_load(driver)
        
        file_items = driver.find_elements(
            By.XPATH,
            "//div[contains(@class,'list-group')]/div[contains(@class,'list-group-item')][position()>1]"
        )
        assert len(file_items) == 2, f"Expected 2 files in dataset, found {len(file_items)}"

        print("Upload ZIP folder test passed!")

    finally:
        close_driver(driver)
        
def test_upload_empty_zip_dataset():
    driver = initialize_driver()
    try:
        host = get_host_for_selenium_testing()

        # Login
        driver.get(f"{host}/login")
        wait_for_page_to_load(driver)
        driver.find_element(By.NAME, "email").send_keys("user1@example.com")
        driver.find_element(By.NAME, "password").send_keys("1234")
        driver.find_element(By.NAME, "password").send_keys(Keys.RETURN)
        time.sleep(3)
        wait_for_page_to_load(driver)

        # Count initial datasets
        initial_datasets = count_datasets(driver, host)

        # Open upload page and fill basic info
        driver.get(f"{host}/dataset/upload")
        wait_for_page_to_load(driver)
        driver.find_element(By.NAME, "title").send_keys("Zip Empty Upload Title")
        driver.find_element(By.NAME, "desc").send_keys("Zip folder upload description")
        driver.find_element(By.NAME, "tags").send_keys("zip,test")

        # Switch upload source to ZIP
        driver.execute_script(
            "const e = document.getElementById('upload-source'); e.value = 'zip'; e.dispatchEvent(new Event('change'));"
        )
        time.sleep(1)
        wait_for_page_to_load(driver)

        # Upload the zip using the hidden dropzone input
        zip_path = os.path.abspath("app/modules/dataset/zip_examples/not_fits.zip")

        dropzone = driver.find_element(By.CLASS_NAME, "dz-hidden-input")
        dropzone.send_keys(zip_path)
        time.sleep(2)
        wait_for_page_to_load(driver)

        # Verify no dataset count increment and warning shown
        warning = WebDriverWait(driver, 5).until(lambda d: d.find_element(By.ID, "alerts"))
        assert warning.is_displayed(), "Warning for no files not displayed"
        assert "No valid FITS files" in warning.text or warning.text.strip() != "", "Warning text is empty or unexpected"
        
        final_datasets = count_datasets(driver, host)
        assert final_datasets == initial_datasets, "Dataset count increased after empty ZIP upload"

        print("Upload empty ZIP test passed!")

    finally:
        close_driver(driver)

def test_view_dataset():
    driver = initialize_driver()

    try:
        host = get_host_for_selenium_testing()

        # Open the login page
        driver.get(f"{host}/login")
        wait_for_page_to_load(driver)

        driver.find_element(By.ID, "email").send_keys("user1@example.com")
        driver.find_element(By.ID, "password").send_keys("1234")
        driver.find_element(By.ID, "submit").click()
        driver.find_element(By.LINK_TEXT, "Sample dataset 4").click()
        driver.find_element(By.CSS_SELECTOR, ".list-group-item:nth-child(2) .btn").click()
        print("View dataset test passed!")

    finally:
        close_driver(driver)


def test_download_counter():
    driver = initialize_driver()

    try:
        host = get_host_for_selenium_testing()
        driver.get(f"{host}/")
        download_counters = len(driver.find_elements(By.ID, "download_counter"))
        datasets = count_home_datasets(driver, host)
        assert download_counters == datasets
        driver.get(f"{host}/login")
        driver.set_window_size(1070, 1002)
        driver.find_element(By.CSS_SELECTOR, ".nav-link:nth-child(1)").click()
        driver.find_element(By.ID, "email").send_keys("user1@example.com")
        driver.find_element(By.ID, "password").send_keys("1234")
        driver.find_element(By.ID, "email").click()
        driver.find_element(By.ID, "email").click()
        driver.find_element(By.ID, "email").click()
        driver.find_element(By.ID, "password").click()
        driver.find_element(By.ID, "submit").click()
        driver.find_element(By.CSS_SELECTOR, ".sidebar-item:nth-child(7) .align-middle:nth-child(2)").click()
        driver.find_element(By.LINK_TEXT, "Sample dataset 3").click()
        driver.find_element(By.ID, "download_counter").click()
        assert driver.find_element(By.ID, "download_counter") is not None
        assert driver.find_element(By.ID, "download_counter").text is not None
        print("Download counter test passed!")
    finally:
        close_driver(driver)


def test_trending_dataset():
    driver = initialize_driver()

    try:
        host = get_host_for_selenium_testing()
        driver.get(f"{host}/")
        trending_datasets = count_trending_datasets(driver, host)
        trending_download_counters = len(driver.find_elements(By.ID, "trending_download_counter"))
        titles = len(driver.find_elements(By.ID, "trending_title"))
        authors = len(driver.find_elements(By.ID, "trending_authors"))
        fire_icon = driver.find_element(By.ID, "fire_icon")
        assert fire_icon is not None
        assert trending_datasets == trending_download_counters == titles == authors
        print("Trending datasets test passed!")
    finally:
        close_driver(driver)


def test_badge():
    driver = initialize_driver()

    try:
        host = get_host_for_selenium_testing()

        # Open the login page
        driver.get(f"{host}/login")
        wait_for_page_to_load(driver)

        driver.find_element(By.ID, "email").send_keys("user1@example.com")
        driver.find_element(By.ID, "password").send_keys("1234")
        driver.find_element(By.ID, "submit").click()
        driver.find_element(By.LINK_TEXT, "Sample dataset 4").click()
        driver.find_element(By.CSS_SELECTOR, ".list-group-item:nth-child(2) .btn").click()

        badge_image = driver.find_element(By.CSS_SELECTOR, ".badge-actions-block img")
        assert badge_image.is_displayed(), "Badge image is not visible"
        badge_src = badge_image.get_attribute("src")
        assert "img.shields.io" in badge_src, "Badge image src is not from shields.io"
        assert "dataset/4/badge.json" in badge_src

        markdown_input = driver.find_element(By.ID, "markdown-input")
        html_input = driver.find_element(By.ID, "html-input")

        markdown_value = markdown_input.get_attribute("value")
        html_value = html_input.get_attribute("value")

        assert markdown_value.startswith("[![Sample dataset 4]"), "Markdown value is incorrect"
        assert "shields.io" in markdown_value, "Markdown value is incorrect"

        assert html_value.startswith("<a href="), "HTML value is incorrect"
        assert "doi/10.1234/dataset4" in html_value, "HTML value is incorrect"
        print("Badge test passed!")

    finally:
        close_driver(driver)


# Call the test function
test_trending_dataset()
test_download_counter()
test_view_dataset()
test_upload_dataset()
test_upload_one_zip_dataset()
test_upload_multiple_zip_dataset()
test_upload_empty_zip_dataset()
test_upload_folder_zip_dataset()
test_badge()
