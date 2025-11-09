from flask_wtf import FlaskForm
from wtforms import SubmitField


class FitsmodelForm(FlaskForm):
    submit = SubmitField("Save fitsmodel")
