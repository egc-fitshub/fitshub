import os
import shutil
from datetime import datetime, timezone

from dotenv import load_dotenv

from app.modules.auth.models import User
from app.modules.dataset.models import Author, DataSet, DSMetaData, DSMetrics, PublicationType
from app.modules.fitsmodel.models import FitsModel, FMMetaData
from app.modules.hubfile.models import Hubfile
from core.seeders.BaseSeeder import BaseSeeder


class DataSetSeeder(BaseSeeder):
    priority = 2  # Lower priority

    def run(self):
        # Retrieve users
        user1 = User.query.filter_by(email="user1@example.com").first()
        user2 = User.query.filter_by(email="user2@example.com").first()

        if not user1 or not user2:
            raise Exception("Users not found. Please seed users first.")

        # Create DSMetrics instance
        ds_metrics = DSMetrics(number_of_models="5")
        seeded_ds_metrics = self.seed([ds_metrics])[0]

        # Create DSMetaData instances
        ds_meta_data_list = [
            DSMetaData(
                deposition_id=1 + i,
                title=f"Sample dataset {i + 1}",
                description=f"Description for dataset {i + 1}",
                publication_type=PublicationType.DATA_MANAGEMENT_PLAN,
                publication_doi=f"10.1234/dataset{i + 1}",
                dataset_doi=f"10.1234/dataset{i + 1}",
                tags="tag1, tag2",
                ds_metrics_id=seeded_ds_metrics.id,
            )
            for i in range(4)
        ]
        seeded_ds_meta_data = self.seed(ds_meta_data_list)

        # Create Author instances and associate with DSMetaData
        authors = [
            Author(
                name=f"Author {i + 1}",
                affiliation=f"Affiliation {i + 1}",
                orcid=f"0000-0000-0000-000{i}",
                ds_meta_data_id=seeded_ds_meta_data[i % 4].id,
            )
            for i in range(4)
        ]
        self.seed(authors)

        # Create DataSet instances
        datasets = [
            DataSet(
                user_id=user1.id if i % 2 == 0 else user2.id,
                ds_meta_data_id=seeded_ds_meta_data[i].id,
                created_at=datetime.now(timezone.utc),
            )
            for i in range(4)
        ]
        seeded_datasets = self.seed(datasets)

        # Assume there are 12 .fits files, create corresponding FMMetaData and FITS Model
        fm_meta_data_list = [
            FMMetaData(
                fits_filename=f"file{i+1}.fits",
                title=f"FITS Model {i+1}",
                description=f"Description for FITS model {i+1}",
                publication_type=PublicationType.SOFTWARE_DOCUMENTATION,
                publication_doi=f"10.1234/fm{i + 1}",
                tags="tag1, tag2",
                fits_version="1.0",
            )
            for i in range(12)
        ]
        seeded_fm_meta_data = self.seed(fm_meta_data_list)

        # Create Author instances and associate with FMMetaData
        fm_authors = [
            Author(
                name=f"Author {i + 5}",
                affiliation=f"Affiliation {i + 5}",
                orcid=f"0000-0000-0000-000{i + 5}",
                fm_meta_data_id=seeded_fm_meta_data[i].id,
            )
            for i in range(12)
        ]
        self.seed(fm_authors)

        fits_models = [
            FitsModel(data_set_id=seeded_datasets[i // 3].id, fm_meta_data_id=seeded_fm_meta_data[i].id)
            for i in range(12)
        ]
        seeded_fits_models = self.seed(fits_models)

        # Create files, associate them with FITS Models and copy files
        load_dotenv()
        working_dir = os.getenv("WORKING_DIR", "")
        src_folder = os.path.join(working_dir, "app", "modules", "dataset", "fits_examples")
        for i in range(12):
            file_name = f"file{i+1}.fits"
            fits_model = seeded_fits_models[i]
            dataset = next(ds for ds in seeded_datasets if ds.id == fits_model.data_set_id)
            user_id = dataset.user_id

            dest_folder = os.path.join(working_dir, "uploads", f"user_{user_id}", f"dataset_{dataset.id}")
            os.makedirs(dest_folder, exist_ok=True)
            shutil.copy(os.path.join(src_folder, file_name), dest_folder)

            file_path = os.path.join(dest_folder, file_name)

            fits_file = Hubfile(
                name=file_name,
                checksum=f"checksum{i + 1}",
                size=os.path.getsize(file_path),
                fits_model_id=fits_model.id,
            )
            self.seed([fits_file])
