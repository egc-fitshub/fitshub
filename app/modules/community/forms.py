from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField
from wtforms import SelectMultipleField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional


class CommunityForm(FlaskForm):
    name = StringField("Community Name", validators=[DataRequired(), Length(max=256)])
    description = TextAreaField("Description", validators=[DataRequired()])
    logo_file = FileField("Logo File", validators=[Optional(), FileAllowed(["jpg", "png", "jpeg"], "Images only!")])
    curator_ids = SelectMultipleField("Additional Curators", coerce=str, choices=[], validators=[Optional()])

    submit = SubmitField("Create Community")


class AddCuratorsForm(FlaskForm):
    curator_ids = SelectMultipleField(
        "Select users to add as curators", coerce=str, choices=[], validators=[Optional()]
    )
    submit = SubmitField("Add Selected Curators")
