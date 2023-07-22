from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, TextAreaField
from wtforms.validators import DataRequired, Email, Length, InputRequired, Optional


class MessageForm(FlaskForm):
    """Form for adding/editing messages."""

    text = TextAreaField('text', validators=[DataRequired()])


class UserAddForm(FlaskForm):
    """Form for adding users."""

    username = StringField('Username', validators=[DataRequired()])
    email = StringField('E-mail', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[Length(min=6)])
    image_url = StringField('(Optional) Image URL')


class LoginForm(FlaskForm):
    """Login form."""

    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[Length(min=6)])

class UserEditForm(FlaskForm):
    """Form for editing user profile details."""

    username = StringField('Username')
    email = StringField('E-mail', validators=[Optional(), Email()])
    image_url = StringField('Profile Picture')
    header_image_url = StringField('Banner Picture')
    bio = StringField('Bio', validators=[Length(max=250)])
    password = PasswordField('Password (Required to change details)', validators=[InputRequired(message="Please provide your password"), Length(min=6)])
