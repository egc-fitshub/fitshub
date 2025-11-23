from app.modules.community.models import Community
from core.repositories.BaseRepository import BaseRepository


class CommunityRepository(BaseRepository):
    def __init__(self):
        super().__init__(Community)
    
    def get_all_communities(self):
        return Community.query.order_by(Community.name.asc()).all()
    
    def create(self, instance, commit: bool = True):
        self.session.add(instance)
        if commit:
            self.session.commit()
        else:
            self.session.flush()
        return instance
