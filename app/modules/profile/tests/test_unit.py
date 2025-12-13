import pytest
from flask import url_for

from app import db
from app.modules.auth.models import User
from app.modules.conftest import login, logout
from app.modules.profile.models import UserProfile


@pytest.fixture(scope="module")
def test_client(test_client):
    """
    Extends the test_client fixture to add additional specific data for module testing.
    for module testing (por example, new users)
    """
    with test_client.application.app_context():
        user_test = User(email="user@example.com", password="test1234")
        db.session.add(user_test)
        db.session.commit()

        profile = UserProfile(user_id=user_test.id, name="John", surname="Smith")
        db.session.add(profile)
        db.session.commit()

        user_with_no_profile = User(email="noprofile@example.com", password="test1234")
        db.session.add(user_with_no_profile)
        db.session.commit()

        user_summary = User(email="summary_user@example.com", password="test1234")
        db.session.add(user_summary)
        db.session.commit()

        profile_summary = UserProfile(user_id=user_summary.id, name="John", surname="Doe")
        db.session.add(profile_summary)
        db.session.commit()

    yield test_client


def test_edit_profile_page_get(test_client):
    """
    Tests access to the profile editing page via a GET request.
    """
    login_response = login(test_client, "user@example.com", "test1234")
    assert login_response.status_code == 200, "Login was unsuccessful."

    response = test_client.get("/profile/edit")
    assert response.status_code == 200, "The profile editing page could not be accessed."
    assert b"Edit profile" in response.data, "The expected content is not present on the page"

    logout(test_client)


def test_edit_profile_post_success(test_client):
    login(test_client, "user@example.com", "test1234")

    form_data = {
        "name": "New Name",
        "surname": "New Surname",
        "orcid": "0000-0000-0000-0000",
        "affiliation": "New Affiliation",
    }
    response = test_client.post("/profile/edit", data=form_data, follow_redirects=True)

    assert response.status_code == 200, "Failed to submit profile edit form."
    assert b"Profile updated successfully" in response.data

    with test_client.application.app_context():
        updatedProfile = UserProfile.query.filter_by(name="New Name").first()
        assert updatedProfile is not None
        assert updatedProfile.surname == "New Surname"

    logout(test_client)


def test_edit_profile_post_failure(test_client):
    login(test_client, "user@example.com", "test1234")

    form_data = {
        "name": "",
        "surname": "",
    }
    response = test_client.post("/profile/edit", data=form_data, follow_redirects=True)
    assert response.status_code == 200, "Failed to submit profile edit form."

    assert b"Edit profile" in response.data

    logout(test_client)


def test_my_profile_get(test_client):
    login(test_client, "summary_user@example.com", "test1234")

    response = test_client.get("/profile/summary")
    assert response.status_code == 200

    assert b"John" in response.data

    logout(test_client)


def test_edit_profile_no_profile(test_client):
    login(test_client, "noprofile@example.com", "test1234")

    response = test_client.get("/profile/edit", follow_redirects=True)
    assert response.request.path == url_for("public.index")

    logout(test_client)
