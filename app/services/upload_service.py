import os
from werkzeug.utils import secure_filename
from flask import current_app

class UploadService:
    @staticmethod
    def save_file(file_storage, folder_name='communities'):
        if not file_storage or not file_storage.filename:
            return None

        upload_dir_base = current_app.config.get('PHOTO_UPLOAD_FOLDER')
        
        if not upload_dir_base:
             raise EnvironmentError("PHOTO_UPLOAD_FOLDER no está configurado en la app.config.")

        filename = secure_filename(file_storage.filename)
        
        target_dir = os.path.join(upload_dir_base, folder_name)
        os.makedirs(target_dir, exist_ok=True)
        file_path = os.path.join(target_dir, filename)
        
        file_storage.save(file_path)

        return f'/static/img/photos/{folder_name}/{filename}'