import base64

import numpy as np
import pytest
from astropy.io import fits

from app.modules.hubfile.routes import (
    get_image_from_fits_headers,
    parse_fits_headers,
)


@pytest.fixture(scope="module")
def test_client(test_client):
    """
    Extends the test_client fixture to add additional specific data for module testing.
    """
    with test_client.application.app_context():
        # Add HERE new elements to the database that you want to exist in the test context.
        # DO NOT FORGET to use db.session.add(<element>) and db.session.commit() to save the data.
        pass

    yield test_client


def test_sample_assertion(test_client):
    """
    Sample test to verify that the test framework and environment are working correctly.
    It does not communicate with the Flask application; it only performs a simple assertion to
    confirm that the tests in this module can be executed.
    """
    greeting = "Hello, World!"
    assert greeting == "Hello, World!", "The greeting does not coincide with 'Hello, World!'"


def test_parse_fits_headers(test_client):
    """
    Test that parse_fits_headers correctly reads and parses FITS headers from a file.
    """
    text = parse_fits_headers("app/modules/dataset/fits_examples/file1.fits")

    assert "SIMPLE" in text
    assert text.count("XTENSION") == 4
    assert text.count("IMAGE") == 3
    assert text.count("BINTABLE") == 1


def test_get_image_from_fits_headers_generates_png(tmp_path):
    """
    Create a small 2D FITS file, call the backend function and verify
    it returns a base64 encoded PNG image.
    """
    data = np.arange(16).reshape((4, 4)).astype(np.float32)
    hdu = fits.PrimaryHDU(data)
    file_path = tmp_path / "test_image.fits"
    hdu.writeto(file_path)

    image_b64 = get_image_from_fits_headers(str(file_path))
    assert isinstance(image_b64, str)
    decoded = base64.b64decode(image_b64)

    assert decoded.startswith(b"\x89PNG\r\n\x1a\n")


def test_get_image_from_fits_headers_invalid_file_raises():
    with pytest.raises(Exception):
        get_image_from_fits_headers("nonexistent_file.fits")
