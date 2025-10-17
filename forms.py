from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField, PasswordField, SelectField, EmailField, IntegerField
from wtforms.fields import DateField
from wtforms.validators import DataRequired, Length, Email
from flask_wtf.file import FileField, FileAllowed, FileRequired

class AppointmentForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(min=2, max=100)])
    email = EmailField('Email', validators=[DataRequired(), Email()]) # EKLENDİ
    phone = StringField('Phone Number', validators=[DataRequired()])
    date = DateField('Preferred Date', format='%Y-%m-%d', validators=[DataRequired()])
    time = SelectField('Preferred Time', validators=[DataRequired()], choices=[])

    # YENİ HİZMET SEÇİM ALANI EKLENDİ
    service = SelectField('Service', validators=[DataRequired()], coerce=int) 

    message = TextAreaField('Message (e.g., design ideas)')
    submit = SubmitField('Book Now')

class AddServiceForm(FlaskForm):
    name = StringField('Service Name', validators=[DataRequired()])
    duration = IntegerField('Duration (minutes)', validators=[DataRequired()])
    submit_service = SubmitField('Add Service')

class PhotoUploadForm(FlaskForm):
    photo = FileField('Photo', validators=[
        FileRequired(),
        FileAllowed(['jpg', 'png', 'jpeg'], 'Images only!')
    ])
    submit_photo = SubmitField('Upload Photo')

class VideoUploadForm(FlaskForm):
    video = FileField('Video', validators=[
        FileRequired(),
        FileAllowed(['mp4', 'mov', 'avi'], 'Videos only!')
    ])
    submit_video = SubmitField('Upload Video')

class LoginForm(FlaskForm):
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')