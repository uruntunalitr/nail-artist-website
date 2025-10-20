from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField, PasswordField, SelectField, EmailField, IntegerField
from wtforms.fields import DateField
from wtforms.validators import DataRequired, Length, Email
from flask_wtf.file import FileField, FileAllowed, FileRequired

class AppointmentForm(FlaskForm):
    name = StringField('Adınız ve Soyadınız', validators=[DataRequired(), Length(min=2, max=100)])
    email = EmailField('E-Posta Adresiniz', validators=[DataRequired(), Email()]) # EKLENDİ
    phone = StringField('Telefon Numaranız', validators=[DataRequired()])
    service = SelectField('Hizmet Seçimi', validators=[DataRequired()], coerce=int) 
    date = DateField('Randevu Tarihi', format='%Y-%m-%d', validators=[DataRequired()])
    time = SelectField('Randevu Saati', validators=[DataRequired()], choices=[])
    message = TextAreaField('Mesajınız (örn: istediğiniz tasarım)')
    submit = SubmitField('Randevu alın')

class AddServiceForm(FlaskForm):
    name = StringField('Hizmet', validators=[DataRequired()])
    duration = IntegerField('Süre (dakika)', validators=[DataRequired()])
    submit_service = SubmitField('Hizmet Ekle')

class PhotoUploadForm(FlaskForm):
    photo = FileField('Fotoğraf', validators=[
        FileRequired(),
        FileAllowed(['jpg', 'png', 'jpeg'], 'Sadece Resim!')
    ])
    submit_photo = SubmitField('Fotoğraf Yükle')

class VideoUploadForm(FlaskForm):
    video = FileField('Video', validators=[
        FileRequired(),
        FileAllowed(['mp4', 'mov', 'avi'], 'Sadece video!')
    ])
    submit_video = SubmitField('Video Yükle')

class LoginForm(FlaskForm):
    password = PasswordField('Şifre', validators=[DataRequired()])
    submit = SubmitField('Giriş')