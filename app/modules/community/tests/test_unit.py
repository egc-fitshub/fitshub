import pytest

from app import db
from app.modules.auth.models import RoleType, User
from app.modules.community.models import Community, CommunityDataSet, CommunityDataSetStatus
from app.modules.conftest import login, logout
from app.modules.dataset.models import DataSet, DSMetaData


@pytest.fixture(scope="module")
def test_client(test_client):
    """
    Extends the test_client fixture to add additional specific data for module testing.
    """
    with test_client.application.app_context():
        curator1 = User(email="curator1@example.com", password="password123", role=RoleType.CURATOR)
        curator2 = User(email="curator2@example.com", password="password123", role=RoleType.CURATOR)
        admin1 = User(email="admin1@example.com", password="password123", role=RoleType.ADMINISTRATOR)
        user1 = User(email="user1@example.com", password="password123", role=RoleType.USER)
        user2 = User(email="user2@example.com", password="password123", role=RoleType.USER)
        db.session.add(curator1)
        db.session.add(curator2)
        db.session.add(admin1)
        db.session.add(user1)
        db.session.add(user2)
        db.session.commit()

        new_community = Community(name="Test Community", description="A community created during testing.")
        db.session.add(new_community)
        db.session.commit()

        new_community.curators.append(curator1)
        db.session.commit()

        ds_meta_data = DSMetaData(
            title="Test Dataset",
            description="A dataset created during testing.",
            publication_type="none",
            publication_doi="10.1234/test.dataset",
        )
        db.session.add(ds_meta_data)
        db.session.commit()

        dataset = DataSet(user_id=1, ds_meta_data_id=ds_meta_data.id)
        db.session.add(dataset)
        db.session.commit()

        association = CommunityDataSet(
            community_id=new_community.id, dataset_id=dataset.id, status=CommunityDataSetStatus.PENDING
        )
        db.session.add(association)
        db.session.commit()

    yield test_client


def test_sample_assertion(test_client):
    """Sample test to verify that the test framework and environment are working correctly."""
    greeting = "Hello, World!"
    assert greeting == "Hello, World!", "The greeting does not coincide with 'Hello, World!'"


def test_get_all_communities(test_client):
    response = test_client.get("/community")
    assert response.status_code == 200, "Failed to retrieve communities"


def test_create_from_form(test_client):
    login(test_client, "curator1@example.com", "password123")

    form_data = {"name": "Form Create Test Community", "description": "A new community for testing purposes."}

    response = test_client.post("/community/create", data=form_data, follow_redirects=True)
    assert response.status_code == 200, f"Failed to create community (status {response.status_code})"

    with test_client.application.app_context():
        c = Community.query.filter_by(name=form_data["name"]).first()
        assert c is not None, "Community not found in DB after create"

    logout(test_client)


def test_create_community(test_client):
    login(test_client, "curator1@example.com", "password123")

    response = test_client.post(
        "/community/create",
        data={"name": "Another New Community", "description": "A description for the new community"},
        follow_redirects=True,
    )

    assert response.status_code == 200, "Failed to create community"
    logout(test_client)


def test_create_community_missing_data(test_client):
    login(test_client, "curator1@example.com", "password123")

    response = test_client.post("/community/create", data={"name": "", "description": ""}, follow_redirects=True)

    assert response.status_code == 200, "Should re-display form with validation errors"

    with test_client.application.app_context():
        empty_name_community = Community.query.filter_by(name="").first()
        assert empty_name_community is None, "Community with empty name should not be created"

    logout(test_client)


def test_update_from_form(test_client):
    login(test_client, "curator1@example.com", "password123")

    form_data = {"name": "Form Update Test Community", "description": "A new community for testing purposes."}

    create_response = test_client.post("/community/create", data=form_data, follow_redirects=True)
    assert create_response.status_code == 200, "Failed to create community for update test"

    with test_client.application.app_context():
        community = Community.query.filter_by(name=form_data["name"]).first()
        assert community is not None, "Community not found after creation"
        community_id = community.id

    form_data_update = {"name": "Updated Community Name", "description": "Updated description."}
    update_response = test_client.post(
        f"/community/{community_id}/update", data=form_data_update, follow_redirects=True
    )
    assert update_response.status_code == 200, "Failed to update community"

    with test_client.application.app_context():
        updated_community = Community.query.get(community_id)
        assert updated_community.name == "Updated Community Name", "Community name was not updated"
        assert updated_community.description == "Updated description.", "Community description was not updated"

    logout(test_client)


def test_update_community(test_client):
    login(test_client, "curator1@example.com", "password123")
    with test_client.application.app_context():
        community = Community.query.first()
        community_id = community.id
    response = test_client.post(
        f"/community/{community_id}/update",
        data={"name": "Updated Community Name v2", "description": "Updated description for the community"},
        follow_redirects=True,
    )
    assert response.status_code == 200, "Failed to update community"
    logout(test_client)


def test_update_community_missing_data(test_client):
    login(test_client, "curator1@example.com", "password123")
    with test_client.application.app_context():
        community = Community.query.first()
        community_id = community.id
    response = test_client.post(
        f"/community/{community_id}/update", data={"name": "", "description": ""}, follow_redirects=True
    )
    assert response.status_code == 200, "Should re-display form with validation errors"
    with test_client.application.app_context():
        unchanged_community = Community.query.get(community_id)
        assert unchanged_community.name != "", "Community name should not be updated to empty"
    logout(test_client)


def test_delete_community(test_client):
    login(test_client, "admin1@example.com", "password123")

    with test_client.application.app_context():
        community = Community.query.first()
        community_id = community.id

    response = test_client.post(f"/community/{community_id}/delete", follow_redirects=True)
    assert response.status_code == 200, "Failed to delete community"

    logout(test_client)


def test_communities_user(test_client):
    login(test_client, "curator1@example.com", "password123")
    response = test_client.get("/my_communities")
    assert response.status_code == 200, "Failed to retrieve user's communities"
    logout(test_client)


def test_community(test_client):
    login(test_client, "curator1@example.com", "password123")
    with test_client.application.app_context():
        community = Community.query.first()
        community_id = community.id
    response = test_client.get(f"/community/{community_id}")
    assert response.status_code == 200, "Failed to retrieve community details"
    logout(test_client)


def test_community_invalid_id(test_client):
    login(test_client, "curator1@example.com", "password123")
    invalid_community_id = 9999
    response = test_client.get(f"/community/{invalid_community_id}")
    assert response.status_code == 404, "Expected not found status code for invalid community ID"
    logout(test_client)


def test_add_curator_invalid_user(test_client):
    login(test_client, "curator1@example.com", "password123")

    form_data = {"name": "Invalid Curator Test Community", "description": "A new community for testing purposes."}
    create_response = test_client.post("/community/create", data=form_data, follow_redirects=True)
    assert create_response.status_code == 200, "Failed to create community for add curator test"

    with test_client.application.app_context():
        community = Community.query.filter_by(name=form_data["name"]).first()
        assert community is not None, "Community not found after creation"
        community_id = community.id

    invalid_user_id = "9999"
    add_curator_response = test_client.post(
        f"/community/{community_id}/add_curators", data={"user_ids_to_add": invalid_user_id}, follow_redirects=True
    )
    assert add_curator_response.status_code == 200, "Should handle invalid user gracefully"

    with test_client.application.app_context():
        community = Community.query.get(community_id)
        curator_ids = [c.id for c in community.curators]
        assert 9999 not in curator_ids, "Invalid user should not be added as curator"

    logout(test_client)


def test_add_curator_to_community_success(test_client):
    login(test_client, "curator1@example.com", "password123")

    form_data = {"name": "Add Curator Success Community", "description": "Testing curator addition"}
    test_client.post("/community/create", data=form_data, follow_redirects=True)

    with test_client.application.app_context():
        community = Community.query.filter_by(name=form_data["name"]).first()
        community_id = community.id

        curator2 = User.query.filter_by(email="curator2@example.com").first()
        curator2_id = str(curator2.id)

    response = test_client.post(
        f"/community/{community_id}/add_curators", data={"curator_ids": [curator2_id]}, follow_redirects=True
    )
    assert response.status_code == 200, "Should add curator successfully"

    with test_client.application.app_context():
        community = Community.query.get(community_id)
        curator_ids = [c.id for c in community.curators]
        assert int(curator2_id) in curator_ids, "Curator2 should be added"

    logout(test_client)


def test_add_curator_not_curator_of_community(test_client):
    login(test_client, "curator2@example.com", "password123")

    with test_client.application.app_context():
        community = Community.query.first()
        community_id = community.id

        curator2 = User.query.filter_by(email="curator2@example.com").first()
        if curator2 in community.curators:
            community.curators.remove(curator2)
            db.session.commit()

        admin1 = User.query.filter_by(email="admin1@example.com").first()
        admin1_id = str(admin1.id)

    response = test_client.post(
        f"/community/{community_id}/add_curators", data={"curator_ids": [admin1_id]}, follow_redirects=True
    )

    assert response.status_code == 200

    logout(test_client)


def test_view_curators(test_client):
    login(test_client, "curator1@example.com", "password123")

    with test_client.application.app_context():
        community = Community.query.first()
        community_id = community.id

    response = test_client.get(f"/community/{community_id}/curators")
    assert response.status_code == 200, "Should display curators page"

    logout(test_client)


def test_view_curators_community_not_found(test_client):
    login(test_client, "curator1@example.com", "password123")

    invalid_community_id = 9999
    response = test_client.get(f"/community/{invalid_community_id}/curators")
    assert response.status_code == 404, "Expected not found status code"

    logout(test_client)


def test_kick_from_community_success(test_client):
    login(test_client, "admin1@example.com", "password123")

    with test_client.application.app_context():
        curator1 = User.query.filter_by(email="curator1@example.com").first()
        curator2 = User.query.filter_by(email="curator2@example.com").first()

        community = Community.query.filter(Community.curators.contains(curator1)).first()
        if not community:
            community = Community.query.first()

        if curator2 not in community.curators.all():
            community.curators.append(curator2)
            db.session.commit()

        community_id = community.id
        curator2_id = curator2.id

        assert community.curators.count() >= 2, "Community must have at least 2 curators"

    response = test_client.post(f"/community/{community_id}/kick/{curator2_id}", follow_redirects=True)
    assert response.status_code == 200, f"Should kick curator successfully, got {response.status_code}"

    logout(test_client)


def test_kick_from_community_not_found(test_client):
    login(test_client, "admin1@example.com", "password123")

    invalid_community_id = 9999
    response = test_client.post(f"/community/{invalid_community_id}/kick/1")
    assert response.status_code == 404, "Expected not found status code"

    logout(test_client)


def test_kick_last_curator(test_client):
    login(test_client, "admin1@example.com", "password123")

    with test_client.application.app_context():
        curator1 = User.query.filter_by(email="curator1@example.com").first()

        single_curator_community = None
        for comm in Community.query.all():
            if comm.curators.count() == 1 and curator1 in comm.curators.all():
                single_curator_community = comm
                break

        if not single_curator_community:
            single_curator_community = Community(name="Single Curator Test Community", description="Only one curator")
            db.session.add(single_curator_community)
            db.session.flush()
            single_curator_community.curators.append(curator1)
            db.session.commit()

        community_id = single_curator_community.id
        curator1_id = curator1.id

    response = test_client.post(f"/community/{community_id}/kick/{curator1_id}", follow_redirects=True)

    assert response.status_code == 200, f"Expected status 200, got {response.status_code}"

    with test_client.application.app_context():
        community = Community.query.get(community_id)
        curator1_refresh = User.query.get(curator1_id)
        assert curator1_refresh in community.curators.all(), "Last curator should not be removed"

    logout(test_client)


def test_leave_community_success(test_client):
    login(test_client, "curator1@example.com", "password123")

    with test_client.application.app_context():
        curator1 = User.query.filter_by(email="curator1@example.com").first()
        curator2 = User.query.filter_by(email="curator2@example.com").first()

        community = Community.query.filter(Community.curators.contains(curator1)).first()

        if not community:
            community = Community(name="Leave Test Community", description="For testing leave")
            db.session.add(community)
            db.session.flush()
            community.curators.append(curator1)

        if curator2 not in community.curators.all():
            community.curators.append(curator2)

        db.session.commit()

        community_id = community.id

        assert community.curators.count() >= 2, "Community must have at least 2 curators for leave test"

    response = test_client.post(f"/community/{community_id}/leave/", follow_redirects=True)
    assert response.status_code == 200, f"Should leave successfully, got {response.status_code}"

    logout(test_client)


def test_leave_community_not_member(test_client):
    login(test_client, "user1@example.com", "password123")
    with test_client.application.app_context():
        community = Community.query.first()
        if community:
            community_id = community.id
        else:
            community = Community(name="Test Community for Leave", description="Test")
            db.session.add(community)
            db.session.commit()
            community_id = community.id

    response = test_client.post(f"/community/{community_id}/leave/", follow_redirects=True)
    assert response.status_code in [200, 403], f"Expected 200 or 403, got {response.status_code}"
    logout(test_client)


def test_leave_community_last_curator(test_client):
    login(test_client, "curator1@example.com", "password123")

    form_data = {"name": "Last Curator Leave Test", "description": "Only one curator"}
    create_response = test_client.post("/community/create", data=form_data, follow_redirects=True)
    assert create_response.status_code == 200, "Community creation should succeed"

    with test_client.application.app_context():
        community = Community.query.filter_by(name=form_data["name"]).first()
        assert community is not None, "Community should be created"
        community_id = community.id

    response = test_client.post(f"/community/{community_id}/leave/", follow_redirects=True)

    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    logout(test_client)


def test_get_communities_associated_to_dataset(test_client):
    login(test_client, "test@example.com", "test1234")

    with test_client.application.app_context():
        dataset = DataSet.query.first()
        dataset_id = dataset.id

    response = test_client.get(f"/dataset/{dataset_id}/propose_to")
    assert response.status_code == 200, "Failed to retrieve communities associated with dataset (propose view)"

    logout(test_client)


def test_select_community_for_proposal(test_client):
    with test_client.application.app_context():
        dataset = DataSet.query.first()
        dataset_id = dataset.id

    response = test_client.get(f"/dataset/{dataset_id}/propose_to")
    assert response.status_code == 200, "Should display available communities"


def test_select_community_for_proposal_invalid_dataset(test_client):
    invalid_dataset_id = 9999
    response = test_client.get(f"/dataset/{invalid_dataset_id}/propose_to")
    assert response.status_code == 404, "Expected not found status code"


def test_propose_dataset(test_client):
    login(test_client, "test@example.com", "test1234")

    with test_client.application.app_context():
        dataset = DataSet.query.first()
        community = Community.query.first()
        dataset_id = dataset.id
        community_id = community.id

    response = test_client.post(f"/community/{community_id}/propose/{dataset_id}", follow_redirects=True)
    assert response.status_code == 200, "Failed to propose dataset to community"

    logout(test_client)


def test_propose_dataset_success(test_client):
    """Test successfully proposing dataset to community."""

    with test_client.application.app_context():
        dataset = DataSet.query.first()
        community = Community.query.first()

        existing_assoc = CommunityDataSet.query.filter_by(community_id=community.id, dataset_id=dataset.id).first()

        if existing_assoc:
            db.session.delete(existing_assoc)
            db.session.commit()

        dataset_id = dataset.id
        community_id = community.id

    response = test_client.post(f"/community/{community_id}/propose/{dataset_id}", follow_redirects=True)
    assert response.status_code == 200, f"Should propose successfully, got {response.status_code}"


def test_propose_dataset_already_proposed(test_client):
    with test_client.application.app_context():
        dataset = DataSet.query.first()
        community = Community.query.first()
        dataset_id = dataset.id
        community_id = community.id

    test_client.post(f"/community/{community_id}/propose/{dataset_id}")
    response = test_client.post(f"/community/{community_id}/propose/{dataset_id}", follow_redirects=True)

    assert response.status_code == 200


def test_approve_dataset_success(test_client):
    login(test_client, "curator1@example.com", "password123")

    with test_client.application.app_context():
        curator1 = User.query.filter_by(email="curator1@example.com").first()
        community = Community.query.filter(Community.curators.contains(curator1)).first()
        dataset = DataSet.query.first()

        association = CommunityDataSet.query.filter_by(community_id=community.id, dataset_id=dataset.id).first()

        if not association:
            association = CommunityDataSet(
                community_id=community.id, dataset_id=dataset.id, status=CommunityDataSetStatus.PENDING
            )
            db.session.add(association)
        else:
            association.status = CommunityDataSetStatus.PENDING

        db.session.commit()

        community_id = community.id
        dataset_id = dataset.id

    response = test_client.post(f"/community/{community_id}/approve/{dataset_id}", follow_redirects=True)
    assert response.status_code == 200, f"Should approve successfully, got {response.status_code}"


    logout(test_client)


def test_reject_dataset_success(test_client):
    login(test_client, "curator1@example.com", "password123")

    with test_client.application.app_context():
        curator1 = User.query.filter_by(email="curator1@example.com").first()
        community = Community.query.filter(Community.curators.contains(curator1)).first()
        dataset = DataSet.query.first()

        association = CommunityDataSet.query.filter_by(community_id=community.id, dataset_id=dataset.id).first()

        if association:
            association.status = CommunityDataSetStatus.PENDING
        else:
            association = CommunityDataSet(
                community_id=community.id, dataset_id=dataset.id, status=CommunityDataSetStatus.PENDING
            )
            db.session.add(association)

        db.session.commit()

        community_id = community.id
        dataset_id = dataset.id

        db.session.close()

    response = test_client.post(f"/community/{community_id}/reject/{dataset_id}", follow_redirects=True)
    assert response.status_code == 200, f"Should reject successfully, got {response.status_code}"

    with test_client.application.app_context():
        association = CommunityDataSet.query.filter_by(community_id=community_id, dataset_id=dataset_id).first()
        assert association.status == CommunityDataSetStatus.REJECTED, (
            f"Dataset should be rejected, got {association.status}"
        )

    logout(test_client)


def test_delete_association(test_client):
    login(test_client, "curator1@example.com", "password123")

    with test_client.application.app_context():
        curator1 = User.query.filter_by(email="curator1@example.com").first()
        community = Community.query.filter(Community.curators.contains(curator1)).first()
        dataset = DataSet.query.first()
        dataset_id = dataset.id
        community_id = community.id

    response = test_client.post(f"/community/{community_id}/reject/{dataset_id}", follow_redirects=True)
    assert response.status_code == 200, "Failed to reject (delete) dataset association"

    logout(test_client)


def test_pending_datasets(test_client):
    login(test_client, "curator1@example.com", "password123")

    with test_client.application.app_context():
        curator1 = User.query.filter_by(email="curator1@example.com").first()
        community = Community.query.filter(Community.curators.contains(curator1)).first()
        community_id = community.id

    response = test_client.get(f"/community/{community_id}/review")
    assert response.status_code == 200, "Failed to retrieve pending datasets (review page)"

    logout(test_client)


def test_review_pending_datasets(test_client):
    login(test_client, "curator1@example.com", "password123")
    with test_client.application.app_context():
        curator1 = User.query.filter_by(email="curator1@example.com").first()
        community = Community.query.filter(Community.curators.contains(curator1)).first()
        community_id = community.id
    response = test_client.get(f"/community/{community_id}/review")
    assert response.status_code == 200, "Failed to access review page"
    logout(test_client)


def test_review_pending_datasets_success(test_client):
    login(test_client, "curator1@example.com", "password123")

    with test_client.application.app_context():
        curator1 = User.query.filter_by(email="curator1@example.com").first()
        community = Community.query.filter(Community.curators.contains(curator1)).first()
        community_id = community.id

    response = test_client.get(f"/community/{community_id}/review")
    assert response.status_code == 200, "Should display pending datasets"

    logout(test_client)


def test_communities_user_not_curator(test_client):
    login(test_client, "user1@example.com", "password123")

    with test_client.application.app_context():
        user1 = User.query.filter_by(email="user1@example.com").first()
        assert user1.role == RoleType.USER, "User1 should have USER role"

    response = test_client.get("/my_communities", follow_redirects=False)

    if response.status_code == 200:
        with test_client.application.app_context():
            user1 = User.query.filter_by(email="user1@example.com").first()
            communities = user1.curated_communities.all()
            assert len(communities) == 0, "User1 should not have any curated communities"
    else:
        assert response.status_code == 403, f"Expected forbidden status code, got {response.status_code}"

    logout(test_client)


def test_update_community_not_curator_or_admin(test_client):
    login(test_client, "user1@example.com", "password123")

    with test_client.application.app_context():
        community = Community.query.first()
        community_id = community.id

    response = test_client.post(f"/community/{community_id}/update", follow_redirects=True)
    assert response.status_code == 403, "Expected forbidden status code"
    logout(test_client)


def test_delete_community_not_curator(test_client):
    login(test_client, "user1@example.com", "password123")

    with test_client.application.app_context():
        community = Community.query.first()
        community_id = community.id

    response = test_client.post(f"/community/{community_id}/delete", follow_redirects=True)
    assert response.status_code == 403, "Expected forbidden status code"
    logout(test_client)


def test_delete_community_not_admin(test_client):
    login(test_client, "curator1@example.com", "password123")

    with test_client.application.app_context():
        community = Community.query.first()
        community_id = community.id

    response = test_client.post(f"/community/{community_id}/delete", follow_redirects=True)
    assert response.status_code == 403, "Expected forbidden status code"
    logout(test_client)


def test_add_curator_no_permission(test_client):
    login(test_client, "user1@example.com", "password123")
    with test_client.application.app_context():
        community = Community.query.first()
        community_id = community.id
    response = test_client.post(
        f"/community/{community_id}/add_curators", data={"email": "new_curator@example.com"}, follow_redirects=True
    )
    assert response.status_code == 403, "Expected forbidden status code"
    logout(test_client)


def test_view_curators_not_curator(test_client):
    login(test_client, "user1@example.com", "password123")

    with test_client.application.app_context():
        community = Community.query.first()
        community_id = community.id

    response = test_client.get(f"/community/{community_id}/curators")
    assert response.status_code == 403, "Expected forbidden status code"

    logout(test_client)


def test_kick_from_community_not_admin(test_client):
    login(test_client, "curator1@example.com", "password123")

    with test_client.application.app_context():
        community = Community.query.first()
        community_id = community.id
        user2 = User.query.filter_by(email="user2@example.com").first()
        user2_id = user2.id

    response = test_client.post(f"/community/{community_id}/kick/{user2_id}")
    assert response.status_code == 403, "Expected forbidden status code"

    logout(test_client)


def test_leave_community_not_curator(test_client):
    login(test_client, "user1@example.com", "password123")

    with test_client.application.app_context():
        community = Community.query.first()
        community_id = community.id

    response = test_client.post(f"/community/{community_id}/leave/")
    assert response.status_code == 403, "Expected forbidden status code"

    logout(test_client)


def test_update_dataset_status_not_curator(test_client):
    login(test_client, "user1@example.com", "password123")
    with test_client.application.app_context():
        dataset = DataSet.query.first()
        community = Community.query.first()
        dataset_id = dataset.id
        community_id = community.id
    response = test_client.post(f"/community/{community_id}/approve/{dataset_id}", follow_redirects=True)
    assert response.status_code == 403, "Expected forbidden status code"
    logout(test_client)


def test_aprove_dataset_no_permission(test_client):
    """Test that user without permission cannot approve datasets."""
    login(test_client, "user1@example.com", "password123")
    with test_client.application.app_context():
        dataset = DataSet.query.first()
        community = Community.query.first()
        dataset_id = dataset.id
        community_id = community.id
    response = test_client.post(f"/community/{community_id}/approve/{dataset_id}", follow_redirects=True)
    assert response.status_code == 403, "Expected forbidden status code"
    logout(test_client)


def test_approve_dataset_not_curator(test_client):
    login(test_client, "user1@example.com", "password123")

    with test_client.application.app_context():
        community = Community.query.first()
        dataset = DataSet.query.first()
        community_id = community.id
        dataset_id = dataset.id

    response = test_client.post(f"/community/{community_id}/approve/{dataset_id}")
    assert response.status_code == 403, "Expected forbidden status code"

    logout(test_client)


def test_reject_dataset_no_permission(test_client):
    login(test_client, "user1@example.com", "password123")
    with test_client.application.app_context():
        dataset = DataSet.query.first()
        community = Community.query.first()
        dataset_id = dataset.id
        community_id = community.id
    response = test_client.post(f"/community/{community_id}/reject/{dataset_id}", follow_redirects=True)
    assert response.status_code == 403, "Expected forbidden status code"
    logout(test_client)


def test_reject_dataset_not_curator(test_client):
    login(test_client, "user1@example.com", "password123")

    with test_client.application.app_context():
        community = Community.query.first()
        dataset = DataSet.query.first()
        community_id = community.id
        dataset_id = dataset.id

    response = test_client.post(f"/community/{community_id}/reject/{dataset_id}")
    assert response.status_code == 403, "Expected forbidden status code"

    logout(test_client)


def test_delete_association_not_curator(test_client):
    login(test_client, "user1@example.com", "password123")
    with test_client.application.app_context():
        dataset = DataSet.query.first()
        community = Community.query.first()
        dataset_id = dataset.id
        community_id = community.id
    response = test_client.post(f"/community/{community_id}/reject/{dataset_id}", follow_redirects=True)
    assert response.status_code == 403, "Expected forbidden status code"
    logout(test_client)


def test_pending_datasets_not_curator(test_client):
    login(test_client, "user1@example.com", "password123")

    with test_client.application.app_context():
        community = Community.query.first()
        community_id = community.id

    response = test_client.get(f"/community/{community_id}/review")
    assert response.status_code == 403, "Expected forbidden status code"
    logout(test_client)


def test_review_pending_datasets_no_permission(test_client):
    login(test_client, "user1@example.com", "password123")
    with test_client.application.app_context():
        community = Community.query.first()
        community_id = community.id
    response = test_client.get(f"/community/{community_id}/review")
    assert response.status_code == 403, "Expected forbidden status code"
    logout(test_client)


def test_review_pending_datasets_not_curator(test_client):
    login(test_client, "user1@example.com", "password123")

    with test_client.application.app_context():
        community = Community.query.first()
        community_id = community.id

    response = test_client.get(f"/community/{community_id}/review")
    assert response.status_code == 403, "Expected forbidden status code"

    logout(test_client)
