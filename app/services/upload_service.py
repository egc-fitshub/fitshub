import os

from flask import current_app
from PIL import Image
from werkzeug.utils import secure_filename


class UploadService:
    DEFAULT_SIZE = (256, 256)

    @staticmethod
    def save_file(file_storage, folder_name="communities"):
        if not file_storage or not file_storage.filename:
            return None

        upload_dir_base = current_app.config.get("PHOTO_UPLOAD_FOLDER")

        if not upload_dir_base:
            raise EnvironmentError("PHOTO_UPLOAD_FOLDER no está configurado en la app.config.")

        filename = secure_filename(file_storage.filename)

        target_dir = os.path.join(upload_dir_base, folder_name)
        os.makedirs(target_dir, exist_ok=True)
        file_path = os.path.join(target_dir, filename)

        file_storage.save(file_path)

        try:
            img = Image.open(file_path)

            img.thumbnail(UploadService.DEFAULT_SIZE)

            img.save(file_path)

        except Exception as e:
            current_app.logger.error(f"Error al procesar la imagen: {e}")
            os.remove(file_path)
            return None

        return f"/static/img/photos/{folder_name}/{filename}"
