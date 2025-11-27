from app.modules.community.models import Community, CommunityDataSet, CommunityDataSetStatus
from core.repositories.BaseRepository import BaseRepository


class CommunityRepository(BaseRepository):
    def __init__(self):
        super().__init__(Community)

    def get_all_communities(self):
        return Community.query.order_by(Community.name.asc()).all()

    def get_existing_comunnity_with_name(self, community_name):
        return Community.query.filter_by(name=community_name).first()


class CommunityDataSetRepository(BaseRepository):
    def __init__(self):
        super().__init__(CommunityDataSet)

    def get_existing_association(self, community_id, dataset_id):
        return CommunityDataSet.query.get((community_id, dataset_id))

    def get_communities_associated_to_dataset(self, dataset_id):
        return CommunityDataSet.query.filter(
            CommunityDataSet.dataset_id == dataset_id, CommunityDataSet.status != CommunityDataSetStatus.REJECTED
        ).all()
