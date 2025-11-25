from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField, SelectMultipleField
from wtforms.validators import DataRequired, Length, Optional
from flask_wtf.file import FileField, FileAllowed, FileRequired


class CommunityForm(FlaskForm):
    name = StringField('Community Name',validators=[DataRequired(),Length(max=256)])
    description = TextAreaField('Description',validators=[DataRequired()])
    logo_file = FileField('Logo File',validators=[
            Optional(), 
            FileAllowed(['jpg', 'png', 'jpeg'], 'Images only!')
        ]
    )
    curator_ids = SelectMultipleField(
        'Additional Curators',
        coerce=str,
        choices=[],
        validators=[Optional()]
    )
    
    submit = SubmitField('Create Community')

class AddCuratorsForm(FlaskForm):
    curator_ids = SelectMultipleField(
        'Select users to add as curators',
        coerce=str,
        choices=[],
        validators=[Optional()]
    )
    submit = SubmitField('Add Selected Curators')


