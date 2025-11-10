from flask import render_template

from app.modules.fitsmodel import fitsmodel_bp


@fitsmodel_bp.route("/fitsmodel", methods=["GET"])
def index():
    return render_template("fitsmodel/index.html")
