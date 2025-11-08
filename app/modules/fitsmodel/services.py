from app.modules.fitsmodel.repositories import FitsmodelRepository
from core.services.BaseService import BaseService


class FitsmodelService(BaseService):
    def __init__(self):
        super().__init__(FitsmodelRepository())
