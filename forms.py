from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField, PasswordField, SelectField
from wtforms.fields import DateField
from wtforms.validators import DataRequired, Length
from flask_wtf.file import FileField, FileAllowed, FileRequired

class AppointmentForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(min=2, max=100)])
    phone = StringField('Phone Number', validators=[DataRequired()])
    date = DateField('Preferred Date', format='%Y-%m-%d', validators=[DataRequired()])
    time = SelectField('Preferred Time', validators=[DataRequired()], choices=[])
    message = TextAreaField('Message (e.g., design ideas)')
    submit = SubmitField('Book Now')

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