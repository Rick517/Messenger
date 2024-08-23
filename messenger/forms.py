from flask_wtf import FlaskForm
from wtforms import SubmitField, StringField, PasswordField, EmailField, TextAreaField
from flask_wtf.file import FileAllowed, FileField
from wtforms.validators import DataRequired, Length, Email, EqualTo
from messenger.models import User


class EmailForm(FlaskForm):
    email = EmailField('Email', validators=[Email(), DataRequired(), Length(max=40)])
    submit = SubmitField('Continue')

    # It is not secure. But it's more important than register multiple accounts with same email.
    def validate_user(self):
        user = User.query.filter_by(email=self.email.data).first()
        return user

class PasswordForm(FlaskForm):
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8, max=40)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password'), Length(min=8, max=40)])
    submit = SubmitField('Reset Password')

# Could I use superclasses?
class LoginForm(EmailForm):
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8, max=40)])
    submit = SubmitField('Log In')
    

class RegistrationForm(PasswordForm, EmailForm):
    first_name = StringField('First Name', validators=[DataRequired(), Length(min=2, max=34)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(min=2, max=20)])
    submit = SubmitField('Create Account')

    

class ContactForm(EmailForm):
    first_name = StringField('First Name', validators=[DataRequired(), Length(max=12)])
    last_name = StringField('Last Name', validators=[Length(max=12)])
    submit = SubmitField('Done')


class EditProfileForm(FlaskForm):
    # Gif = insecure to jafar attacks
    avatar = FileField('Avatar', validators=[FileAllowed(['jpg', 'png', 'gif'])])
    first_name = StringField('First Name', validators=[DataRequired(), Length(min=2, max=34)])
    last_name = StringField('Last Name', validators=[Length(max=20)])
    bio = TextAreaField('Biography', validators=[Length(max=70)])
    submit = SubmitField('Update')


class ReportBugForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(min=8, max=40)])
    description = TextAreaField('Description', validators=[DataRequired(), Length(min=100, max=1000)])
    device = StringField('Device', validators=[DataRequired(), Length(min=2, max=40)])
    web_browser = StringField('Web Browser', validators=[DataRequired(), Length(min=3, max=26)])
    messenger_version = StringField('Messenger Version', validators=[DataRequired(), Length(min=2, max=20)])
    country = StringField('Country', validators=[DataRequired(), Length(min=2, max=40)])
    submit = SubmitField('Report')

class NewGroupForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(min=2, max=34)])
    image = FileField('Image', validators=[FileAllowed(['jpg', 'png'])])
    submit = SubmitField('Create Group')

