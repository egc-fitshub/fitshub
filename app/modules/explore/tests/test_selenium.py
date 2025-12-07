from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

from core.environment.host import get_host_for_selenium_testing
from core.selenium.common import close_driver, initialize_driver

DEFAULT_TIMEOUT = 10


def wait_for_page_to_load(driver, timeout=DEFAULT_TIMEOUT):
    WebDriverWait(driver, timeout).until(lambda d: d.execute_script("return document.readyState") == "complete")


def set_input_value(element, value):
    element.clear()
    element.send_keys(value)


def get_field_value(driver, element_id):
    return driver.find_element(By.ID, element_id).get_attribute("value")


def open_explore_page(driver):
    host = get_host_for_selenium_testing()
    driver.get(f"{host}/explore")
    wait_for_page_to_load(driver)
    WebDriverWait(driver, DEFAULT_TIMEOUT).until(EC.visibility_of_element_located((By.ID, "filters-panel")))
    return host


def test_explore_filters_render_base_state():
    driver = initialize_driver()

    try:
        open_explore_page(driver)

        required_ids = [
            "results-container",
            "no-results",
            "search-query-filter",
            "filter-publication-type",
            "filter-sorting",
            "filter-tags",
            "filter-date-from",
            "filter-date-to",
            "clear-filters",
        ]

        for element_id in required_ids:
            element = driver.find_element(By.ID, element_id)
            assert element.is_displayed(), f"{element_id} should be visible"

        select = Select(driver.find_element(By.ID, "filter-publication-type"))
        assert len(select.options) >= 1, "Publication type options should be loaded"

        sorting_select = driver.find_element(By.ID, "filter-sorting")
        assert sorting_select.get_attribute("value") == "newest"

        date_error = driver.find_element(By.ID, "date-error")
        assert "d-none" in date_error.get_attribute("class"), "Date error should be hidden initially"

    finally:
        close_driver(driver)


def test_explore_date_range_validation():
    driver = initialize_driver()

    try:
        open_explore_page(driver)

        date_from = driver.find_element(By.ID, "filter-date-from")
        date_to = driver.find_element(By.ID, "filter-date-to")
        date_error = driver.find_element(By.ID, "date-error")

        set_input_value(date_from, "2024-06-10")
        set_input_value(date_to, "2024-05-10")

        WebDriverWait(driver, DEFAULT_TIMEOUT).until(lambda _: "d-none" not in date_error.get_attribute("class"))
        assert "is-invalid" in date_to.get_attribute("class"), "End date should be marked invalid"

        set_input_value(date_to, "2024-07-10")
        WebDriverWait(driver, DEFAULT_TIMEOUT).until(lambda _: "d-none" in date_error.get_attribute("class"))
        assert "is-invalid" not in date_to.get_attribute("class"), "End date should be valid again"

    finally:
        close_driver(driver)


def test_clear_filters_button_resets_inputs():
    driver = initialize_driver()

    try:
        open_explore_page(driver)

        query_field = driver.find_element(By.ID, "search-query-filter")
        pub_select = Select(driver.find_element(By.ID, "filter-publication-type"))
        tags_field = driver.find_element(By.ID, "filter-tags")
        date_from = driver.find_element(By.ID, "filter-date-from")
        date_to = driver.find_element(By.ID, "filter-date-to")
        sorting_select = Select(driver.find_element(By.ID, "filter-sorting"))

        query_field.send_keys("Galaxies")

        selected_value = None
        for option in pub_select.options:
            value = option.get_attribute("value")
            if value:
                pub_select.select_by_value(value)
                selected_value = value
                break

        tags_field.send_keys("radio,infrared")
        set_input_value(date_from, "2024-01-01")
        set_input_value(date_to, "2024-12-31")
        sorting_select.select_by_value("oldest")

        driver.find_element(By.ID, "clear-filters").click()

        wait = WebDriverWait(driver, DEFAULT_TIMEOUT)
        wait.until(lambda _: query_field.get_attribute("value") == "")
        wait.until(lambda _: get_field_value(driver, "filter-tags") == "")
        wait.until(lambda _: get_field_value(driver, "filter-date-from") == "")
        wait.until(lambda _: get_field_value(driver, "filter-date-to") == "")
        wait.until(lambda _: get_field_value(driver, "filter-sorting") == "newest")

        if selected_value:
            wait.until(lambda _: get_field_value(driver, "filter-publication-type") == "")

    finally:
        close_driver(driver)


if __name__ == "__main__":
    test_explore_filters_render_base_state()
    test_explore_date_range_validation()
    test_clear_filters_button_resets_inputs()
