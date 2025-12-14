import logging

from flask import current_app
from flask_login import current_user

from app.modules.auth.models import User
from app.modules.auth.services import AuthenticationService
from app.modules.community.models import CommunityDataSet, CommunityDataSetStatus
from app.modules.community.repositories import CommunityDataSetRepository, CommunityRepository
from app.modules.dataset.services import DataSetService
from app.services.upload_service import UploadService
from core.services.BaseService import BaseService
from app.modules.elasticsearch.utils import (
                index_dataset,
                index_hubfile,
            )

logger = logging.getLogger(__name__)


class CommunityService(BaseService):
    def __init__(self):
        super().__init__(CommunityRepository())
        self.upload_service = UploadService()
        self.user_service = AuthenticationService()

    def get_all_communities(self):
        return self.repository.get_all_communities()

    def create_from_form(self, form_data, logo_file):
        try:
            existing_community = self.repository.get_existing_comunnity_with_name(form_data.name.data)

            if existing_community:
                form_data.name.errors.append(f'A community with the name "{form_data.name.data}" already exists.')
                return None

            logo_url = self.upload_service.save_file(logo_file, "communities") if logo_file else None

            community = {"name": form_data.name.data, "description": form_data.description.data, "logo_url": logo_url}

            new_community = self.repository.create(commit=False, **community)

            creator_id = current_user.id

            selected_ids = [int(i) for i in form_data.curator_ids.data if i]

            if creator_id not in selected_ids:
                selected_ids.append(creator_id)

            curators_to_assign = User.query.filter(User.id.in_(selected_ids)).all()

            new_community.curators.extend(curators_to_assign)
            self.repository.session.commit()

            return new_community

        except Exception as e:
            self.repository.session.rollback()
            current_app.logger.error(f"FALLO AL CREAR LA COMUNIDAD: {e}", exc_info=True)
            return {"error": str(e)}

    def update_from_form(self, community_id, form_data, logo_file):
        try:
            update_data = {}

            if logo_file:
                logo_url = self.upload_service.save_file(logo_file, "communities")
                update_data["logo_url"] = logo_url

            update_data["name"] = form_data.name.data
            update_data["description"] = form_data.description.data
            updated_community = self.repository.update(community_id, **update_data)

            self.repository.session.commit()

            return updated_community

        except Exception as e:
            self.repository.session.rollback()
            current_app.logger.error(f"FALLO AL ACTUALIZAR LA COMUNIDAD: {e}", exc_info=True)
            return {"error": str(e)}

    def leave_community(self, community_id, user_id):
        community = self.repository.get_or_404(community_id)
        user = self.user_service.get_or_404(user_id)

        if not user or not community:
            return {"error": "User or community not found"}

        if user not in community.curators.all():
            return {"error": f"User {user_id} is not a curator of community {community_id}."}

        try:
            if community.curators.count() <= 1:
                return {"error": "The community must have at least one curator. Cannot leave if you are the only one."}

            community.curators.remove(user)
            self.repository.session.commit()

            return {"success": f"User {user.email} successfully left community {community.name}."}

        except Exception as e:
            self.repository.session.rollback()
            current_app.logger.error(f"FALLO AL ABANDONAR LA COMUNIDAD: {e}", exc_info=True)
            return {"error": "An unexpected error occurred while processing the request."}

    def add_curator(self, community_id, user_ids_to_add_str):
        try:
            community = self.repository.get_or_404(community_id)

            if not community:
                return {"error": "Community not found."}

            user_ids_to_add = [int(i) for i in user_ids_to_add_str if i]
            new_curators = User.query.filter(User.id.in_(user_ids_to_add)).all()

            if not user_ids_to_add:
                return {"error": "No users were selected."}

            users_already_curators = [u.id for u in community.curators.all()]

            users_to_add = [user for user in new_curators if user.id not in users_already_curators]

            if not users_to_add:
                return {"error": "All selected users are already curators of this community."}

            community.curators.extend(users_to_add)
            self.repository.session.commit()

            count = len(users_to_add)
            return {"success": f"{count} new curator(s) added successfully to {community.name}."}

        except Exception as e:
            self.repository.session.rollback()
            current_app.logger.error(f"FALLO AL AÑADIR CURADORES: {e}", exc_info=True)
            return {"error": str(e)}


class CommunityDataSetService(BaseService):
    def __init__(self):
        super().__init__(CommunityDataSetRepository())
        self.dataset_service = DataSetService()
        self.community_service = CommunityService()
        self.community_repository = CommunityRepository()

    def get_communities_associated_to_dataset(self, dataset_id):
        return self.repository.get_communities_associated_to_dataset(dataset_id)

    def propose_dataset(self, community_id, dataset_id):
        try:
            community = self.community_service.get_or_404(community_id)
            dataset = self.dataset_service.get_or_404(dataset_id)

            if not dataset or not community:
                return {"error": "Dataset or community not found"}

            existing_association = self.repository.get_existing_association(
                community_id=community_id, dataset_id=dataset_id
            )

            if existing_association:
                if existing_association.status == CommunityDataSetStatus.ACCEPTED:
                    return {"error": "Dataset already accepted in this community."}
                elif existing_association.status == CommunityDataSetStatus.PENDING:
                    return {"error": "Dataset is already pending review in this community."}

                existing_association.status = CommunityDataSetStatus.PENDING
                self.repository.session.commit()
                return existing_association

            new_association = self.repository.create(
                community_id=community_id, dataset_id=dataset_id, status=CommunityDataSetStatus.PENDING
            )

            return new_association

        except Exception as e:
            self.repository.session.rollback()
            logger.error(f"FALLO AL PROPONER DATASET: {e}", exc_info=True)
            return {"error": str(e)}

    def update_dataset_status(self, community_id, dataset_id, new_status):
        try:
            association = self.repository.get_existing_association(community_id=community_id, dataset_id=dataset_id)

            if not association:
                return {"error": "Association not found."}

            if new_status == "accepted":
                new_status = CommunityDataSetStatus.ACCEPTED
            elif new_status == "rejected":
                new_status = CommunityDataSetStatus.REJECTED
            else:
                return {"error": "Invalid status provided."}

            association.status = new_status
            self.repository.session.commit()
            if new_status == CommunityDataSetStatus.ACCEPTED:
                index_dataset(association.dataset)
                fitsmodels = list(association.dataset.fits_models)
                for f in fitsmodels:
                    files = list(getattr(f, "files", []))
                    for hubfile in files:
                        index_hubfile(hubfile)
            return association

        except Exception as e:
            self.repository.session.rollback()
            current_app.logger.error(f"FALLO AL ACTUALIZAR ESTADO DE DATASET: {e}", exc_info=True)
            return {"error": str(e)}

    def get_pending_datasets(self, community_id):
        community = self.community_repository.get_or_404(community_id)
        return community.dataset_associations.filter(CommunityDataSet.status == CommunityDataSetStatus.PENDING).all()
