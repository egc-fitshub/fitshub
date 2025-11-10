from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, Length


class SignupForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(max=100)])
    surname = StringField("Surname", validators=[DataRequired(), Length(max=100)])
    password = PasswordField("Password", validators=[DataRequired()])
    email = StringField("Email", validators=[DataRequired(), Email()])
    submit = SubmitField("Submit")


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    remember_me = BooleanField("Remember me")
    submit = SubmitField("Login")


class ForgotPasswordForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    submit = SubmitField("Send Reset Link")


class ResetPasswordForm(FlaskForm):
    password = PasswordField("New Password", validators=[DataRequired()])
    submit = SubmitField("Reset Password")
