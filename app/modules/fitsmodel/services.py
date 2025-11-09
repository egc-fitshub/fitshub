from app.modules.fitsmodel.repositories import FitsModelRepository, FMMetaDataRepository
from app.modules.hubfile.services import HubfileService
from core.services.BaseService import BaseService


class FitsModelService(BaseService):
    def __init__(self):
        super().__init__(FitsModelRepository())
        self.hubfile_service = HubfileService()

    def total_fits_model_views(self) -> int:
        return self.hubfile_service.total_hubfile_views()

    def total_fits_model_downloads(self) -> int:
        return self.hubfile_service.total_hubfile_downloads()

    def count_fits_models(self):
        return self.repository.count_fits_models()

    class FMMetaDataService(BaseService):
        def __init__(self):
            super().__init__(FMMetaDataRepository())
