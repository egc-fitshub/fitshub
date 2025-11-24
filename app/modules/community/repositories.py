from app.modules.community.models import Community, CommunityDataSet, CommunityDataSetStatus
from core.repositories.BaseRepository import BaseRepository


class CommunityRepository(BaseRepository):
    def __init__(self):
        super().__init__(Community)
    
    def get_all_communities(self):
        return Community.query.order_by(Community.name.asc()).all()
    
class CommunityDataSetRepository(BaseRepository):
    def __init__(self):
        super().__init__(CommunityDataSet)
        
    def get_existing_association(self, community_id, dataset_id):
        return CommunityDataSet.query.get((community_id, dataset_id))
