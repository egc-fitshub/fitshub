from app.modules.community.repositories import CommunityRepository
from core.services.BaseService import BaseService
from app.modules.community.models import Community
from app.modules.auth.models import User
from flask_login import current_user
from flask import current_app
from app.services.upload_service import UploadService


class CommunityService(BaseService):
    def __init__(self):
        super().__init__(CommunityRepository())
        self.upload_service = UploadService()
        
    def get_all_communities(self):
        return self.repository.get_all_communities()

    def create(self, form_data, logo_file):
        try:
            logo_url = self.upload_service.save_file(logo_file, 'communities') if logo_file else None
            
            new_community = Community(
                name=form_data.name.data,
                description=form_data.description.data,
                logo_url=logo_url
            )
            
            creator_id = current_user.id 
            
            selected_ids = [int(i) for i in form_data.curator_ids.data if i]
            
            if creator_id not in selected_ids:
                selected_ids.append(creator_id)
                
            curators_to_assign = User.query.filter(User.id.in_(selected_ids)).all()
            
            new_community.curators.extend(curators_to_assign)
            self.repository.create(new_community) 
            
            return new_community
        
        except Exception as e:
            current_app.logger.error(f"FALLO AL CREAR LA COMUNIDAD: {e}", exc_info=True)
            return {'error': str(e)}