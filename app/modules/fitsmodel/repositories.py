from sqlalchemy import func

from app.modules.fitsmodel.models import FitsModel, FMMetaData
from core.repositories.BaseRepository import BaseRepository


class FitsModelRepository(BaseRepository):
    def __init__(self):
        super().__init__(FitsModel)

    def count_fits_models(self) -> int:
        max_id = self.model.query.with_entities(func.max(self.model.id)).scalar()
        return max_id if max_id is not None else 0


class FMMetaDataRepository(BaseRepository):
    def __init__(self):
        super().__init__(FMMetaData)
