import logging

from flask import render_template

from app.modules.dataset.services import DataSetService
from app.modules.fitsmodel.services import FitsModelService
from app.modules.public import public_bp

logger = logging.getLogger(__name__)


@public_bp.route("/")
def index():
    logger.info("Access index")
    dataset_service = DataSetService()
    fits_model_service = FitsModelService()

    # Statistics: total datasets and FITS models
    datasets_counter = dataset_service.count_synchronized_datasets()
    fits_models_counter = fits_model_service.count_fits_models()

    # Statistics: total downloads
    total_dataset_downloads = dataset_service.total_dataset_downloads()
    total_fits_model_downloads = fits_model_service.total_fits_model_downloads()

    # Statistics: total views
    total_dataset_views = dataset_service.total_dataset_views()
    total_fits_model_views = fits_model_service.total_fits_model_views()

    # Get trending datasets
    trending_datasets = dataset_service.get_trending_datasets(limit=5, period_days=7)

    return render_template(
        "public/index.html",
        datasets=dataset_service.latest_synchronized(),
        trending_datasets=trending_datasets,
        datasets_counter=datasets_counter,
        fits_models_counter=fits_models_counter,
        total_dataset_downloads=total_dataset_downloads,
        total_fits_model_downloads=total_fits_model_downloads,
        total_dataset_views=total_dataset_views,
        total_fits_model_views=total_fits_model_views,
    )
