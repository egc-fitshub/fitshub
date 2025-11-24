import logging
from app.modules.community.repositories import (
    CommunityRepository,
    CommunityDataSetRepository
)
from core.services.BaseService import BaseService
from app.modules.community.models import (
    Community,
    CommunityDataSetStatus,
    CommunityDataSet
)
from app.modules.auth.models import User
from flask_login import current_user
from flask import current_app
from app.services.upload_service import UploadService
from app.modules.dataset.services import DataSetService
from app.modules.auth.services import AuthenticationService

logger = logging.getLogger(__name__)

class CommunityService(BaseService):
    def __init__(self):
        super().__init__(CommunityRepository())
        self.upload_service = UploadService()
        
    def get_all_communities(self):
        return self.repository.get_all_communities()

    def create_from_form(self, form_data, logo_file):
        try:
            logo_url = self.upload_service.save_file(logo_file, 'communities') if logo_file else None
            
            community = {
                'name': form_data.name.data,
                'description': form_data.description.data,
                'logo_url': logo_url
            }
            
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
            return {'error': str(e)}
     
class CommunityDataSetService(BaseService):
    def __init__(self):
        super().__init__(CommunityDataSetRepository())
        self.dataset_service = DataSetService()
        self.community_service = CommunityService()
        self.community_repository = CommunityRepository()
    
    def propose_dataset(self, community_id, dataset_id):
        try: 
            community = self.community_service.get_or_404(community_id)
            dataset = self.dataset_service.get_or_404(dataset_id)
            
            if not dataset or not community:
                return {'error':'Dataset or community not found'}
            
            existing_association = self.repository.get_existing_association(
                community_id=community_id, dataset_id=dataset_id)
            
            if existing_association:
                if existing_association.status == CommunityDataSetStatus.ACCEPTED:
                    return {'error': 'Dataset already accepted in this community.'}
                elif existing_association.status == CommunityDataSetStatus.PENDING:
                    return {'error': 'Dataset is already pending review in this community.'}
                
                existing_association.status = CommunityDataSetStatus.PENDING
                self.repository.session.commit()
                return existing_association
            
            new_association = self.repository.create(
                community_id=community_id,
                dataset_id=dataset_id,
                status=CommunityDataSetStatus.PENDING
            )
            
            return new_association

        except Exception as e:
            self.repository.session.rollback()
            logger.error(f"FALLO AL PROPONER DATASET: {e}", exc_info=True)
            return {'error': str(e)}
    
    def update_dataset_status(self, community_id, dataset_id, new_status):
        try:
            association = self.repository.get_existing_association(
                community_id=community_id, dataset_id=dataset_id)
            
            if not association:
                return {'error': 'Association not found.'}
             
            if new_status == "accepted":
                new_status = CommunityDataSetStatus.ACCEPTED
            elif new_status == "rejected":
                new_status = CommunityDataSetStatus.REJECTED
            else:
                return {'error': 'Invalid status provided.'}
            
            association.status = new_status
            self.repository.session.commit()
            
            return association

        except Exception as e:
            self.repository.session.rollback()
            current_app.logger.error(f"FALLO AL ACTUALIZAR ESTADO DE DATASET: {e}", exc_info=True)
            return {'error': str(e)}
    
    def get_pending_datasets(self, community_id):
        community = self.community_repository.get_or_404(community_id)
        return community.dataset_associations.filter(
            CommunityDataSet.status == CommunityDataSetStatus.PENDING
        ).all() 
        
    def delete_association(self, community_id, dataset_id):
        try:
            association = self.repository.get_existing_association(
                community_id=community_id, dataset_id=dataset_id)
            
            if not association:
                return {'error': 'Association not found.'}
            
            self.repository.session.delete(association)
            self.repository.session.commit()
            
            return {'success': f'Association between Community {community_id} and Dataset {dataset_id} deleted successfully.'}
        
        except Exception as e:
            self.repository.session.rollback()
            current_app.logger.error(f"FALLO AL BORRAR ASOCIACIÓN: {e}", exc_info=True)
            return {'error': str(e)}