from app.modules.fitsmodel.models import Fitsmodel
from core.repositories.BaseRepository import BaseRepository


class FitsmodelRepository(BaseRepository):
    def __init__(self):
        super().__init__(Fitsmodel)
