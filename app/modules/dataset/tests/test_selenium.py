import os
import re
import time

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait

from core.environment.host import get_host_for_selenium_testing
from core.selenium.common import close_driver, initialize_driver


def login(driver, host):
    """Helper function to log in a user."""
    driver.get(f"{host}/login")
    wait_for_page_to_load(driver)

    # Add cookie to indicate testing mode
    driver.execute_script("document.cookie = 'SELENIUM_TEST=1; path=/';")

    # Find the username and password field and enter the values
    email_field = driver.find_element(By.NAME, "email")
    password_field = driver.find_element(By.NAME, "password")

    email_field.send_keys("user1@example.com")
    password_field.send_keys("1234")

    # Send the form
    password_field.send_keys(Keys.RETURN)
    time.sleep(4)
    wait_for_page_to_load(driver)


def upload_agree_and_submit(driver):
    """Helper function to agree to terms and submit uploads form."""
    # Check I agree and send form
    check = driver.find_element(By.ID, "agreeCheckbox")
    check.send_keys(Keys.SPACE)
    wait_for_page_to_load(driver)

    upload_btn = driver.find_element(By.ID, "upload_button")
    upload_btn.send_keys(Keys.RETURN)
    wait_for_page_to_load(driver)
    time.sleep(2)


def switch_upload_source(driver, source):
    """Helper function to switch upload source."""
    driver.execute_script(
        f"const e = document.getElementById('upload-source'); e.value = '{source}'; "
        + "e.dispatchEvent(new Event('change'));"
    )
    time.sleep(1)
    wait_for_page_to_load(driver)


def upload_to_dropzone(driver, file_path):
    """Helper function to upload a file to the dropzone."""
    path = os.path.abspath("app/modules/dataset/" + file_path)

    dropzone = driver.find_element(By.CLASS_NAME, "dz-hidden-input")
    dropzone.send_keys(path)
    time.sleep(2)
    wait_for_page_to_load(driver)


def add_github_repo(driver, repo_url):
    """Helper function to add a GitHub repository URL."""
    gh_input = driver.find_element(By.ID, "github_url")
    gh_input.clear()
    gh_input.send_keys(repo_url)
    driver.find_element(By.ID, "github_fetch_btn").click()


def wait_for_page_to_load(driver, timeout=4):
    WebDriverWait(driver, timeout).until(
        lambda driver: driver.execute_script("return document.readyState") == "complete"
    )


def wait_for_element(driver, by, value, timeout=10):
    """Wait until an element is present and return it."""
    return WebDriverWait(driver, timeout).until(lambda d: d.find_element(by, value))


def open_dataset_detail_by_title(driver, host, title):
    """Helper function to open dataset detail page by title. Generated with the help of GitHub Copilot."""
    rows = driver.find_elements(By.XPATH, "//table//tbody//tr")
    for r in rows:
        # Try to find anchors in the title cell or actions column
        anchors = r.find_elements(By.XPATH, ".//td[1]//a | .//td[4]//a")
        for a in anchors:
            try:
                text = a.text.strip()
            except Exception:
                text = ""
            # If the anchor text matches the requested title, follow it
            if text == title:
                href = a.get_attribute("href")
                m = re.search(r"(https?://[^/]+)?(/.*)$", href)
                path = m.group(2) if m else href
                driver.get(f"{host}{path}")
                wait_for_page_to_load(driver)
                return True

        # Fallback: compare the title cell text
        try:
            title_cell = r.find_element(By.XPATH, ".//td[1]")
            if title_cell.text.strip() == title:
                title_cell.click()
                wait_for_page_to_load(driver)
                return True
        except Exception:
            # ignore and continue to next row
            pass

    return False


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
    """Test uploading a dataset with two FITS files."""
    driver = initialize_driver()

    try:
        host = get_host_for_selenium_testing()

        login(driver, host)

        # Count initial datasets
        initial_datasets = count_datasets(driver, host)

        # Open the upload dataset
        driver.get(f"{host}/dataset/upload")
        wait_for_page_to_load(driver)

        # Find basic info and FITS model and fill values
        title_field = wait_for_element(driver, By.NAME, "title")
        title_field.send_keys("Title")
        desc_field = wait_for_element(driver, By.NAME, "desc")
        desc_field.send_keys("Description")
        tags_field = wait_for_element(driver, By.NAME, "tags")
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
        dropzone = wait_for_element(driver, By.CLASS_NAME, "dz-hidden-input")
        dropzone.send_keys(file1_path)
        wait_for_page_to_load(driver)

        # Subir el segundo archivo
        dropzone = wait_for_element(driver, By.CLASS_NAME, "dz-hidden-input")
        dropzone.send_keys(file2_path)
        wait_for_page_to_load(driver)

        # Add authors in FITS models
        show_button = wait_for_element(driver, By.ID, "0_button")
        show_button.send_keys(Keys.RETURN)
        add_author_fits_button = wait_for_element(driver, By.ID, "0_form_authors_button")
        add_author_fits_button.send_keys(Keys.RETURN)
        wait_for_page_to_load(driver)

        name_field = wait_for_element(driver, By.NAME, "fits_models-0-authors-2-name")
        name_field.send_keys("Author3")
        affiliation_field = wait_for_element(driver, By.NAME, "fits_models-0-authors-2-affiliation")
        affiliation_field.send_keys("Club3")

        upload_agree_and_submit(driver)

        assert driver.current_url == f"{host}/dataset/list", "Test failed!"

        # Count final datasets
        final_datasets = count_datasets(driver, host)
        assert final_datasets == initial_datasets + 1, "Test failed!"

        print("Test upload dataset passed!")

    finally:
        # Close the browser
        close_driver(driver)


def test_upload_one_zip_dataset():
    """Test uploading a ZIP file with one FITS file."""
    driver = initialize_driver()
    try:
        host = get_host_for_selenium_testing()

        # Login
        login(driver, host)

        # Count initial datasets
        initial_datasets = count_datasets(driver, host)

        # Open upload page and fill basic info
        driver.get(f"{host}/dataset/upload")
        wait_for_page_to_load(driver)
        wait_for_element(driver, By.NAME, "title").send_keys("Zip Upload Title")
        wait_for_element(driver, By.NAME, "desc").send_keys("Zip upload description")
        wait_for_element(driver, By.NAME, "tags").send_keys("zip,test")

        switch_upload_source(driver, "zip")

        upload_to_dropzone(driver, "zip_examples/one_fits.zip")

        upload_agree_and_submit(driver)

        # Verify redirect and dataset count increment
        assert driver.current_url == f"{host}/dataset/list", "Upload via ZIP did not redirect to dataset list"
        final_datasets = count_datasets(driver, host)
        assert final_datasets == initial_datasets + 1, "Dataset count did not increase after ZIP upload"

        print("Upload one ZIP dataset test passed!")

    finally:
        close_driver(driver)


def test_upload_multiple_zip_dataset():
    """Test uploading a ZIP file containing multiple FITS files."""
    driver = initialize_driver()
    try:
        host = get_host_for_selenium_testing()

        login(driver, host)

        # Count initial datasets
        initial_datasets = count_datasets(driver, host)

        # Open upload page and fill basic info
        driver.get(f"{host}/dataset/upload")
        wait_for_page_to_load(driver)
        wait_for_element(driver, By.NAME, "title").send_keys("Zip Multiple Upload Title")
        wait_for_element(driver, By.NAME, "desc").send_keys("Zip multiple upload description")
        wait_for_element(driver, By.NAME, "tags").send_keys("zip,test")

        switch_upload_source(driver, "zip")

        upload_to_dropzone(driver, "zip_examples/multiple_fits.zip")

        upload_agree_and_submit(driver)

        # Verify redirect and dataset count increment
        assert driver.current_url == f"{host}/dataset/list", "Upload via ZIP did not redirect to dataset list"
        final_datasets = count_datasets(driver, host)
        assert final_datasets == initial_datasets + 1, "Dataset count did not increase after ZIP upload"

        # Click the detail link
        open_dataset_detail_by_title(driver, host, "Zip Multiple Upload Title")

        file_items = driver.find_elements(
            By.XPATH, "//div[contains(@class,'list-group')]/div[contains(@class,'list-group-item')][position()>1]"
        )
        assert len(file_items) == 2, f"Expected 2 files in dataset, found {len(file_items)}"

        print("Upload multiple ZIP datasets test passed!")

    finally:
        close_driver(driver)


def test_upload_folder_zip_dataset():
    """Test uploading a ZIP file containing a folder with FITS files."""
    driver = initialize_driver()
    try:
        host = get_host_for_selenium_testing()

        login(driver, host)

        # Count initial datasets
        initial_datasets = count_datasets(driver, host)

        # Open upload page and fill basic info
        driver.get(f"{host}/dataset/upload")
        wait_for_page_to_load(driver)
        wait_for_element(driver, By.NAME, "title").send_keys("Zip Folder Upload Title")
        wait_for_element(driver, By.NAME, "desc").send_keys("Zip folder upload description")
        wait_for_element(driver, By.NAME, "tags").send_keys("zip,test")

        switch_upload_source(driver, "zip")

        upload_to_dropzone(driver, "zip_examples/fits_in_folder.zip")

        upload_agree_and_submit(driver)

        # Verify redirect and dataset count increment
        assert driver.current_url == f"{host}/dataset/list", "Upload via ZIP did not redirect to dataset list"
        final_datasets = count_datasets(driver, host)
        assert final_datasets == initial_datasets + 1, "Dataset count did not increase after ZIP upload"

        # Click the detail link
        # Use helper to open dataset detail by title which is more robust
        open_dataset_detail_by_title(driver, host, "Zip Folder Upload Title")

        file_items = driver.find_elements(
            By.XPATH, "//div[contains(@class,'list-group')]/div[contains(@class,'list-group-item')][position()>1]"
        )
        assert len(file_items) == 2, f"Expected 2 files in dataset, found {len(file_items)}"

        print("Upload ZIP folder test passed!")

    finally:
        close_driver(driver)


def test_upload_empty_zip_dataset():
    """Test uploading a ZIP with no FITS files."""
    driver = initialize_driver()
    try:
        host = get_host_for_selenium_testing()

        login(driver, host)

        # Count initial datasets
        initial_datasets = count_datasets(driver, host)

        # Open upload page and fill basic info
        driver.get(f"{host}/dataset/upload")
        wait_for_page_to_load(driver)
        wait_for_element(driver, By.NAME, "title").send_keys("Zip Empty Upload Title")
        wait_for_element(driver, By.NAME, "desc").send_keys("Zip folder upload description")
        wait_for_element(driver, By.NAME, "tags").send_keys("zip,test")

        switch_upload_source(driver, "zip")

        upload_to_dropzone(driver, "zip_examples/not_fits.zip")

        # Verify no dataset count increment and warning shown
        warning = WebDriverWait(driver, 5).until(lambda d: d.find_element(By.ID, "alerts"))
        assert warning.is_displayed(), "Warning for no files not displayed"
        assert "No valid FITS files" in warning.text or warning.text.strip() != "", (
            "Warning text is empty or unexpected"
        )

        final_datasets = count_datasets(driver, host)
        assert final_datasets == initial_datasets, "Dataset count increased after empty ZIP upload"

        print("Upload empty ZIP test passed!")

    finally:
        close_driver(driver)


def test_upload_from_github():
    """Test uploading a dataset from a GitHub repository."""
    driver = initialize_driver()
    try:
        host = get_host_for_selenium_testing()

        login(driver, host)

        # Open upload page and fill basic info
        driver.get(f"{host}/dataset/upload")
        wait_for_page_to_load(driver)
        wait_for_element(driver, By.NAME, "title").send_keys("GitHub Upload Title")
        wait_for_element(driver, By.NAME, "desc").send_keys("GitHub upload description")
        wait_for_element(driver, By.NAME, "tags").send_keys("github,test")

        # Select GitHub as source and trigger UI update
        switch_upload_source(driver, "github")

        # Fill GitHub repo URL and click fetch button
        add_github_repo(driver, "https://github.com/egc-fitshub/fits_test")

        # Wait and check for rate limit warning or file list
        time.sleep(10)
        WebDriverWait(driver, 15).until(
            lambda d: d.find_elements(By.CSS_SELECTOR, "#file-list li") or d.find_elements(By.ID, "github_error")
        )

        errors = driver.find_elements(By.ID, "github_error")
        if errors and errors[0].is_displayed():
            warning = errors[0]
            if "403" in warning.text:
                print("GitHub API rate limit reached; skipping GitHub upload test.")
            else:
                raise AssertionError(f"GitHub error during fetch: {warning.text}")
        else:
            # Check the files have been listed
            file_items = driver.find_elements(By.CSS_SELECTOR, "#file-list li")
            assert len(file_items) == 2, "Not all files listed from GitHub repository"

            upload_agree_and_submit(driver)
            wait_for_page_to_load(driver)

            # Assert that the first upload has the correct title, then open the dataset page
            title_elements = driver.find_elements(By.LINK_TEXT, "GitHub Upload Title")
            assert len(title_elements) > 0, "Uploaded dataset title not found"
            assert title_elements[0].text == "GitHub Upload Title", "Uploaded dataset title does not match"

            # Open dataset detail page via helper to avoid following external DOI links
            open_dataset_detail_by_title(driver, host, "GitHub Upload Title")

            # Assert that the files have been uploaded correctly to the dataset
            file_items = driver.find_elements(
                By.XPATH, "//div[contains(@class,'list-group')]/div[contains(@class,'list-group-item')][position()>1]"
            )
            assert len(file_items) == 2, f"Expected 2 files in dataset, found {len(file_items)}"

            print("Upload from GitHub test passed!")

    finally:
        close_driver(driver)


def test_upload_from_github_non_existing_repo():
    """Test uploading a dataset from a non-existing GitHub repository."""
    driver = initialize_driver()
    try:
        host = get_host_for_selenium_testing()

        login(driver, host)

        # Open upload page and fill basic info
        driver.get(f"{host}/dataset/upload")
        wait_for_page_to_load(driver)
        wait_for_element(driver, By.NAME, "title").send_keys("GitHub Upload Title")
        wait_for_element(driver, By.NAME, "desc").send_keys("GitHub upload description")
        wait_for_element(driver, By.NAME, "tags").send_keys("github,test")

        # Select GitHub as source and trigger UI update
        switch_upload_source(driver, "github")

        # Fill GitHub repo URL and click fetch button
        add_github_repo(driver, "https://github.com/egc-fitshub/non_existing_repo")

        # Wait and check for rate limit warning or error
        time.sleep(10)
        WebDriverWait(driver, 10).until(
            lambda d: d.find_elements(By.ID, "github_error") or d.find_elements(By.CSS_SELECTOR, "#file-list li")
        )

        warning_elems = driver.find_elements(By.ID, "github_error")
        if warning_elems and "403" in warning_elems[0].text:
            print("GitHub API rate limit reached; skipping non-existing GitHub repository upload test.")
        else:
            assert warning_elems and "404" in warning_elems[0].text, "Expected 404 error for non-existing repository"
            print("Upload from GitHub non-existing repository test passed!")

    finally:
        close_driver(driver)


def test_upload_from_github_invalid_repo():
    """Test uploading a dataset from an invalid GitHub repository."""
    driver = initialize_driver()
    try:
        host = get_host_for_selenium_testing()

        login(driver, host)

        # Open upload page and fill basic info
        driver.get(f"{host}/dataset/upload")
        wait_for_page_to_load(driver)
        wait_for_element(driver, By.NAME, "title").send_keys("GitHub Upload Title")
        wait_for_element(driver, By.NAME, "desc").send_keys("GitHub upload description")
        wait_for_element(driver, By.NAME, "tags").send_keys("github,test")

        # Select GitHub as source and trigger UI update
        switch_upload_source(driver, "github")

        # Fill GitHub repo URL and click fetch button
        add_github_repo(driver, "Not a valid URL")

        # Wait and check for correct warning
        try:
            WebDriverWait(driver, 10).until(lambda d: d.find_elements(By.ID, "github_error"))
        except Exception:
            pass

        warning = driver.find_elements(By.ID, "github_error")
        assert warning and "Invalid GitHub repository URL" in warning[0].text, "Expected invalid repo warning"
        print("Upload from GitHub invalid repository test passed!")

    finally:
        close_driver(driver)


def test_upload_from_github_empty_entry():
    """Test uploading a dataset  from Github url with empty entry."""
    driver = initialize_driver()
    try:
        host = get_host_for_selenium_testing()

        login(driver, host)

        # Open upload page and fill basic info
        driver.get(f"{host}/dataset/upload")
        wait_for_page_to_load(driver)
        wait_for_element(driver, By.NAME, "title").send_keys("GitHub Upload Title")
        wait_for_element(driver, By.NAME, "desc").send_keys("GitHub upload description")
        wait_for_element(driver, By.NAME, "tags").send_keys("github,test")

        # Select GitHub as source and trigger UI update
        switch_upload_source(driver, "github")

        # Fill GitHub repo URL and click fetch button
        add_github_repo(driver, "")

        # Wait and check warning is shown
        try:
            WebDriverWait(driver, 10).until(lambda d: d.find_elements(By.ID, "github_error"))
        except Exception:
            pass

        warning = driver.find_elements(By.ID, "github_error")
        assert warning and "Please enter a GitHub repository URL" in warning[0].text, "Expected empty URL warning"
        print("Upload from GitHub empty entry test passed!")

    finally:
        close_driver(driver)


def test_view_dataset():
    """Test viewing a dataset."""
    driver = initialize_driver()

    try:
        host = get_host_for_selenium_testing()

        #  Login
        login(driver, host)

        # Ensure we're on the dataset list page, then navigate to a dataset page
        driver.get(f"{host}/dataset/list")
        wait_for_page_to_load(driver)

        open_dataset_detail_by_title(driver, host, "Sample dataset 3")
        driver.find_element(By.CSS_SELECTOR, ".list-group-item:nth-child(2) .btn").click()

        print("View dataset test passed!")

    finally:
        close_driver(driver)


def test_download_counter():
    """Test download counter functionality."""
    driver = initialize_driver()

    try:
        # Check download counters in home
        host = get_host_for_selenium_testing()
        driver.get(f"{host}/")
        download_counters = len(driver.find_elements(By.ID, "download_counter"))
        datasets = count_home_datasets(driver, host)
        assert download_counters == datasets

        # Login
        login(driver, host)

        # Check download counter in dataset view
        driver.get(f"{host}/dataset/list")
        wait_for_page_to_load(driver)

        open_dataset_detail_by_title(driver, host, "Sample dataset 3")
        driver.find_element(By.ID, "download_counter").click()
        assert driver.find_element(By.ID, "download_counter") is not None
        assert driver.find_element(By.ID, "download_counter").text is not None

        print("Download counter test passed!")
    finally:
        close_driver(driver)


def test_trending_dataset():
    """Test trending datasets functionality."""
    driver = initialize_driver()

    try:
        # Go to home
        host = get_host_for_selenium_testing()
        driver.get(f"{host}/")

        # Check trending datasets components
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


def test_badge_is_shown():
    """Test that the dataset badge is shown correctly."""
    driver = initialize_driver()

    try:
        host = get_host_for_selenium_testing()

        # Login
        login(driver, host)

        # Navigate to the dataset list, then to a dataset page and check badge is visible
        driver.get(f"{host}/dataset/list")
        wait_for_page_to_load(driver)

        open_dataset_detail_by_title(driver, host, "Sample dataset 3")
        driver.find_element(By.CSS_SELECTOR, ".list-group-item:nth-child(2) .btn").click()

        badge_image = driver.find_element(By.CSS_SELECTOR, ".badge-actions-block img")
        assert badge_image.is_displayed(), "Badge image is not visible"
        badge_src = badge_image.get_attribute("src")
        assert "img.shields.io" in badge_src, "Badge image src is not from shields.io"
        assert re.search(r"dataset/\d+/badge\.json", badge_src), f"Badge src unexpected: {badge_src}"

        # Check markdown and HTML copy values are correct
        markdown_input = driver.find_element(By.ID, "markdown-input")
        html_input = driver.find_element(By.ID, "html-input")

        markdown_value = markdown_input.get_attribute("value")
        html_value = html_input.get_attribute("value")

        assert markdown_value.startswith("[![Sample dataset 3]"), "Markdown value is incorrect"
        assert "shields.io" in markdown_value, "Markdown value is incorrect"

        assert html_value.startswith("<a href="), "HTML value is incorrect"
        assert "doi/10.1234/dataset3" in html_value, "HTML value is incorrect"
        print("Badge test passed!")

    finally:
        close_driver(driver)
