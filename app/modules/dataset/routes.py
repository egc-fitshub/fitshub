from datetime import datetime, timezone
import json
import logging
import os
import re
import shutil
import tempfile
import uuid
from zipfile import ZipFile

import requests
from flask import (
    current_app,
    abort,
    jsonify,
    make_response,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from flask_login import current_user, login_required

from app.modules.dataset import dataset_bp
from app.modules.dataset.forms import DataSetForm
from app.modules.dataset.models import DataSet, DSDownloadRecord
from app.modules.dataset.services import (
    AuthorService,
    DataSetService,
    DOIMappingService,
    DSDownloadRecordService,
    DSMetaDataService,
    DSViewRecordService,
)
from app.modules.fakenodo.services import FakenodoService

logger = logging.getLogger(__name__)


dataset_service = DataSetService()
author_service = AuthorService()
dsmetadata_service = DSMetaDataService()
fakenodo_service = FakenodoService()
doi_mapping_service = DOIMappingService()
ds_view_record_service = DSViewRecordService()


@dataset_bp.route("/dataset/<int:dataset_id>/badge.json")
def generate_json_badge_data(dataset_id):
    """
    Genera un endpoint JSON para ser usado por shields.io
    con el formato 'endpoint'.
    """
    try:
        dataset = DataSet.query.get_or_404(dataset_id)
        meta = dataset.ds_meta_data
        download_counter = str(dataset.download_counter)
        doi_full_url = meta.dataset_doi or "N/A"

        match = re.search(r"(10\.\d{4,9}/[-._;()/:A-Z0-9]+)", doi_full_url, re.IGNORECASE)

        if match:
            doi = match.group(1)
        else:
            doi = doi_full_url

        badge_data = {"schemaVersion": 1, "label": doi, "message": download_counter, "color": "blue"}

        return jsonify(badge_data)

    except Exception as e:
        print(f"Error generando JSON para badge: {e}")
        return jsonify({"schemaVersion": 1, "label": "Error", "message": "Badge no disponible", "color": "red"}), 500


@dataset_bp.route("/dataset/upload", methods=["GET", "POST"])
@login_required
def create_dataset():
    form = DataSetForm()
    if request.method == "POST":
        dataset = None

        if not form.validate_on_submit():
            return jsonify({"message": form.errors}), 400

        try:
            logger.info("Creating dataset...")
            dataset = dataset_service.create_from_form(form=form, current_user=current_user)
            logger.info(f"Created dataset: {dataset}")
            dataset_service.move_fits_models(dataset)
        except Exception as exc:
            logger.exception(f"Exception while create dataset data in local {exc}")
            return jsonify({"Exception while create dataset data in local: ": str(exc)}), 400

        # send dataset as deposition to Fakenodo
        data = {}
        try:
            fakenodo_response_json = fakenodo_service.create_new_deposition(dataset)
            response_data = json.dumps(fakenodo_response_json)
            data = json.loads(response_data)
        except Exception as exc:
            data = {}
            fakenodo_response_json = {}
            logger.exception(f"Exception while create dataset data in Fakenodo {exc}")

        if data.get("conceptrecid"):
            deposition_id = data.get("id")

            try:
                # iterate for each feature model (one feature model = one request to Fakenodo)
                for fits_model in dataset.fits_models:
                    fakenodo_service.upload_file(dataset, deposition_id, fits_model)

                # publish deposition
                fakenodo_service.publish_deposition(deposition_id)

                # update DOI
                deposition_doi = fakenodo_service.get_doi(deposition_id)
                dataset_service.update_dsmetadata(
                    dataset.ds_meta_data_id,
                    deposition_id=deposition_id,
                    dataset_doi=deposition_doi,
                )
            except Exception as e:
                msg = f"it has not been possible upload feature models in Fakenodo and update the DOI: {e}"
                return jsonify({"message": msg}), 200

        # Delete temp folder
        file_path = current_user.temp_folder()
        if os.path.exists(file_path) and os.path.isdir(file_path):
            shutil.rmtree(file_path)

        msg = "Everything works!"
        return jsonify({"message": msg}), 200

    return render_template("dataset/upload_dataset.html", form=form)


@dataset_bp.route("/dataset/list", methods=["GET", "POST"])
@login_required
def list_dataset():
    return render_template(
        "dataset/list_datasets.html",
        datasets=dataset_service.get_synchronized(current_user.id),
        local_datasets=dataset_service.get_unsynchronized(current_user.id),
    )


def generate_temp_filename(filename):
    temp_folder = current_user.temp_folder()
    file_path = os.path.join(temp_folder, filename)

    if os.path.exists(file_path):
        # Generate unique filename (by recursion)
        base_name, extension = os.path.splitext(filename)
        i = 1
        while os.path.exists(os.path.join(temp_folder, f"{base_name} ({i}){extension}")):
            i += 1
        new_filename = f"{base_name} ({i}){extension}"
        file_path = os.path.join(temp_folder, new_filename)
    else:
        new_filename = filename

    return (file_path, new_filename)


def save_file_to_temp(file):
    temp_folder = current_user.temp_folder()

    # create temp folder
    if not os.path.exists(temp_folder):
        os.makedirs(temp_folder)

    file_path, new_filename = generate_temp_filename(file.filename)
    file.save(file_path)
    return (file_path, new_filename)


@dataset_bp.route("/dataset/file/upload", methods=["POST"])
@login_required
def upload():
    file = request.files["file"]

    if not file or not file.filename.endswith(".fits"):
        return jsonify({"message": "No valid file"}), 400

    try:
        file_path, new_filename = save_file_to_temp(file)
    except Exception as e:
        return jsonify({"message": str(e)}), 500

    return (
        jsonify(
            {
                "message": "FITS uploaded and validated successfully",
                "filename": new_filename,
            }
        ),
        200,
    )


@dataset_bp.route("/dataset/file/upload/zip", methods=["POST"])
@login_required
def upload_zip():
    file = request.files["file"]
    new_fits_names = []

    if not file or not file.filename.endswith(".zip"):
        return jsonify({"message": "No valid file"}), 400

    try:
        file_path, new_filename = save_file_to_temp(file)
    except Exception as e:
        return jsonify({"message": str(e)}), 500

    with ZipFile(file_path) as zip:
        names = zip.namelist()
        fits_names = [name for name in names if name.endswith(".fits")]

        for fits_name in fits_names:
            fits_path, fits_filename = generate_temp_filename(os.path.basename(fits_name))
            new_fits_names.append(fits_filename)

            with zip.open(fits_name, mode="r") as fits:
                with open(fits_path, mode="wb") as out:
                    out.write(fits.read())

    os.remove(file_path)

    return (
        jsonify(
            {
                "message": "ZIP uploaded successfully",
                "filenames": new_fits_names,
            }
        ),
        200,
    )


@dataset_bp.route("/dataset/github/fetch", methods=["POST"])
def github_fetch():
    user = request.args.get("user")
    repo = request.args.get("repo")

    if not user or not repo:
        return jsonify({"error": "User or repo not specified"}), 400

    if current_app.config.get("FLASK_ENV") == "testing":
        files = [
            {
                "name": "file1.fits",
                "path": "file1.fits",
                "type": "file",
                "download_url": f"{request.host_url}app/modules/dataset/fits_examples/file1.fits",
            },
            {
                "name": "file2.fits",
                "path": "file2.fits",
                "type": "file",
                "download_url": f"{request.host_url}app/modules/dataset/fits_examples/file2.fits",
            },
        ]
        return jsonify({"filenames": [f["name"] for f in files]}), 200

    # 1. List repository files
    list_url = f"https://api.github.com/repos/{user}/{repo}/contents/"
    try:
        r = requests.get(list_url)
        r.raise_for_status()
        files = r.json()
    except Exception as e:
        return jsonify({"error": f"Error listing repo contents: {e}"}), 500

    # Get list of .fits files
    fits_files = [f["name"] for f in files if f["name"].lower().endswith(".fits")]

    if not fits_files:
        return jsonify({"filenames": []}), 200

    new_fits_names = []

    temp_folder = current_user.temp_folder()

    if not os.path.exists(temp_folder):
        os.makedirs(temp_folder)

    for fits_name in fits_files:
        file_url = f"https://api.github.com/repos/{user}/{repo}/contents/{fits_name}"
        try:
            fr = requests.get(file_url)
            fr.raise_for_status()
            file_info = fr.json()

            download_url = file_info.get("download_url")
            if not download_url:
                return jsonify({"error": f"No download URL for {fits_name}"}), 500

            rfile = requests.get(download_url, stream=True)
            rfile.raise_for_status()

            fits_path, fits_filename = generate_temp_filename(os.path.basename(fits_name))
            new_fits_names.append(fits_filename)

            with open(fits_path, mode="wb") as out:
                out.write(rfile.content)

        except Exception as e:
            return jsonify({"error": f"Error downloading {fits_name}: {e}"}), 500

    return (
        jsonify(
            {
                "message": "Github files uploaded successfully",
                "filenames": new_fits_names,
            }
        ),
        200,
    )


@dataset_bp.route("/dataset/file/delete", methods=["POST"])
def delete():
    data = request.get_json()
    filename = data.get("file")
    temp_folder = current_user.temp_folder()
    filepath = os.path.join(temp_folder, filename)

    if os.path.exists(filepath):
        os.remove(filepath)
        return jsonify({"message": "File deleted successfully"})

    return jsonify({"error": "Error: File not found"})


@dataset_bp.route("/dataset/download/<int:dataset_id>", methods=["GET"])
def download_dataset(dataset_id):
    dataset = dataset_service.get_or_404(dataset_id)

    file_path = f"uploads/user_{dataset.user_id}/dataset_{dataset.id}/"

    temp_dir = tempfile.mkdtemp()
    zip_path = os.path.join(temp_dir, f"dataset_{dataset_id}.zip")

    with ZipFile(zip_path, "w") as zipf:
        for subdir, dirs, files in os.walk(file_path):
            for file in files:
                full_path = os.path.join(subdir, file)

                relative_path = os.path.relpath(full_path, file_path)

                zipf.write(
                    full_path,
                    arcname=os.path.join(os.path.basename(zip_path[:-4]), relative_path),
                )

    user_cookie = request.cookies.get("download_cookie")
    if not user_cookie:
        user_cookie = str(uuid.uuid4())  # Generate a new unique identifier if it does not exist
        # Save the cookie to the user's browser
        resp = make_response(
            send_from_directory(
                temp_dir,
                f"dataset_{dataset_id}.zip",
                as_attachment=True,
                mimetype="application/zip",
            )
        )
        resp.set_cookie("download_cookie", user_cookie)
    else:
        resp = send_from_directory(
            temp_dir,
            f"dataset_{dataset_id}.zip",
            as_attachment=True,
            mimetype="application/zip",
        )

    # Check if the download record already exists for this cookie
    existing_record = DSDownloadRecord.query.filter_by(
        user_id=current_user.id if current_user.is_authenticated else None,
        dataset_id=dataset_id,
        download_cookie=user_cookie,
    ).first()

    if not existing_record:
        # Record the download in your database
        DSDownloadRecordService().create(
            user_id=current_user.id if current_user.is_authenticated else None,
            dataset_id=dataset_id,
            download_date=datetime.now(timezone.utc),
            download_cookie=user_cookie,
        )

        DataSetService().update_download_counter(dataset_id=dataset_id)

    return resp


@dataset_bp.route("/doi/<path:doi>/", methods=["GET"])
def subdomain_index(doi):
    # Check if the DOI is an old DOI
    new_doi = doi_mapping_service.get_new_doi(doi)
    if new_doi:
        # Redirect to the same path with the new DOI
        return redirect(url_for("dataset.subdomain_index", doi=new_doi), code=302)

    # Try to search the dataset by the provided DOI (which should already be the new one)
    ds_meta_data = dsmetadata_service.filter_by_doi(doi)

    if not ds_meta_data:
        abort(404)

    # Get dataset
    dataset = ds_meta_data.data_set

    # Save the cookie to the user's browser
    user_cookie = ds_view_record_service.create_cookie(dataset=dataset)
    resp = make_response(render_template("dataset/view_dataset.html", dataset=dataset))
    resp.set_cookie("view_cookie", user_cookie)

    return resp


@dataset_bp.route("/dataset/unsynchronized/<int:dataset_id>/", methods=["GET"])
@login_required
def get_unsynchronized_dataset(dataset_id):
    # Get dataset
    dataset = dataset_service.get_unsynchronized_dataset(current_user.id, dataset_id)

    if not dataset:
        abort(404)

    return render_template("dataset/view_dataset.html", dataset=dataset)
