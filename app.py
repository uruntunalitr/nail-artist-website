from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import os
from forms import AppointmentForm, PhotoUploadForm, VideoUploadForm, LoginForm
from datetime import datetime, timedelta
import pytz

app = Flask(__name__)
# IMPORTANT: Change this secret key!
app.config['SECRET_KEY'] = 'a_very_secret_key_change_it'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
db = SQLAlchemy(app)

WORKING_HOURS_START = 9  # Sabah 9
WORKING_HOURS_END = 18   # Akşam 6 (18:00'e kadar çalışılıyor, 18:00 randevu değil)
APPOINTMENT_DURATION_MINUTES = 60 # Her randevu 60 dakika sürer

# --- Database Models ---


class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    date = db.Column(db.String(20), nullable=False)
    time = db.Column(db.String(10), nullable=False)
    message = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), nullable=False, default='booked') # 'booked' veya 'blocked'


class Photo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(120), nullable=False)
    position = db.Column(db.Integer, nullable=False)


class Video(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(120), nullable=False)
    position = db.Column(db.Integer, nullable=False)

# --- Routes (Web Pages) ---


@app.route('/')
def index():
    return render_template('index.html', title='Home')


@app.route('/book', methods=['GET', 'POST'])
def book():
    form = AppointmentForm()

    # Eğer form POST metodu ile gönderildiyse
    if request.method == 'POST':
        # Formdan gelen tarihi al
        selected_date_str = request.form.get('date')
        if selected_date_str:
            # O tarihe ait müsait saatleri tekrar hesapla
            # get_available_slots fonksiyonunun mantığını burada tekrar kullanıyoruz
            selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
            booked_appointments = Appointment.query.filter_by(date=selected_date_str).all()
            booked_times = [datetime.strptime(appt.time, '%H:%M').time() for appt in booked_appointments]

            turkey_tz = pytz.timezone('Europe/Istanbul')
            now_in_turkey = datetime.now(turkey_tz)

            possible_slots = []
            start_time = datetime.strptime(f"{WORKING_HOURS_START}:00", '%H:%M')
            end_time = datetime.strptime(f"{WORKING_HOURS_END}:00", '%H:%M')
            current_time_slot = start_time
            while current_time_slot < end_time:
                slot_time = current_time_slot.time()
                slot_datetime = turkey_tz.localize(datetime.combine(selected_date, slot_time))
                if slot_time not in booked_times and slot_datetime > now_in_turkey:
                    possible_slots.append(slot_time.strftime('%H:%M'))
                current_time_slot += timedelta(minutes=APPOINTMENT_DURATION_MINUTES)

            # 'time' alanının seçeneklerini bu müsait saatlerle doldur
            form.time.choices = [(slot, slot) for slot in possible_slots]

    # Şimdi formu doğrula
    if form.validate_on_submit():
        # Doğrulama başarılıysa randevuyu kaydet
        new_appointment = Appointment(
            name=form.name.data,
            phone=form.phone.data,
            date=form.date.data.strftime('%Y-%m-%d'),
            time=form.time.data, # .strftime('%H:%M') artık gerekmiyor
            message=form.message.data,
            status='booked'
        )
        db.session.add(new_appointment)
        db.session.commit()
        flash('Your appointment has been booked successfully!', 'success')
        return redirect(url_for('index'))

    return render_template('book.html', title='Book Appointment', form=form)


ADMIN_PASSWORD = "admin123"


@app.route('/login', methods=['GET', 'POST'])
def login():
    # If admin is already logged in, redirect them to the dashboard
    if 'admin_logged_in' in session:
        return redirect(url_for('admin'))

    form = LoginForm()
    if form.validate_on_submit():
        if form.password.data == ADMIN_PASSWORD:
            # Store login state in the session
            session['admin_logged_in'] = True
            flash('You have been logged in!', 'success')
            return redirect(url_for('admin'))
        else:
            flash('Login Unsuccessful. Please check password', 'danger')
    return render_template('login.html', title='Admin Login', form=form)


@app.route('/logout')
def logout():
    session.pop('admin_logged_in', None)  # Clear the session
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))


@app.route('/admin', methods=['GET', 'POST'])
def admin():
    # This is the security check. If not in session, redirect to login.
    if 'admin_logged_in' not in session:
        return redirect(url_for('login'))

    photo_form = PhotoUploadForm()
    video_form = VideoUploadForm()

    # V-- THIS IS THE CORRECTED LOGIC --V

    # Check if the photo form's submit button was clicked and the form is valid# In app.py, inside the admin() function

    # Inside the photo upload logic
    if photo_form.submit_photo.data and photo_form.validate_on_submit():
        file = photo_form.photo.data
        if file:
            # Calculate the next position
            max_pos = db.session.query(
                db.func.max(Photo.position)).scalar() or 0

            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            # Save the new photo with its position
            new_photo = Photo(filename=filename, position=max_pos + 1)
            db.session.add(new_photo)
            db.session.commit()
            flash('Photo uploaded successfully!', 'success')
            return redirect(url_for('admin'))

    # Inside the video upload logic
    if video_form.submit_video.data and video_form.validate_on_submit():
        file = video_form.video.data
        if file:
            # Calculate the next position
            max_pos = db.session.query(
                db.func.max(Video.position)).scalar() or 0

            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            # Save the new video with its position
            new_video = Video(filename=filename, position=max_pos + 1)
            db.session.add(new_video)
            db.session.commit()
            flash('Video uploaded successfully!', 'success')
            return redirect(url_for('admin'))

    # ^-- END OF CORRECTED LOGIC --^

    # This part remains the same, it fetches all data to display on the page
    appointments = Appointment.query.order_by(Appointment.date.desc()).all()
    photos = Photo.query.order_by(Photo.position).all()
    videos = Video.query.order_by(Video.position).all()

    return render_template('admin.html', title='Admin Panel',
                           appointments=appointments, photos=photos, videos=videos,
                           photo_form=photo_form, video_form=video_form)


@app.route('/move/<item_type>/<int:item_id>/<direction>')
def move_item(item_type, item_id, direction):
    if 'admin_logged_in' not in session:
        # For background requests, it's better to send an error response
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401

    Model = Photo if item_type == 'photo' else Video
    item_to_move = Model.query.get(item_id)

    if not item_to_move:
        return jsonify({'success': False, 'error': 'Item not found'}), 404

    if direction == 'up':
        item_to_swap = Model.query.filter(Model.position < item_to_move.position).order_by(Model.position.desc()).first()
    else: # direction == 'down'
        item_to_swap = Model.query.filter(Model.position > item_to_move.position).order_by(Model.position.asc()).first()

    if item_to_swap:
        # Swap positions
        pos1 = item_to_move.position
        pos2 = item_to_swap.position
        item_to_move.position = pos2
        item_to_swap.position = pos1
        db.session.commit()
        return jsonify({'success': True})

    # If there's nothing to swap with (e.g., moving top item up), just confirm
    return jsonify({'success': False, 'error': 'Cannot move further'})


@app.route('/gallery')
def gallery():
    photos = Photo.query.order_by(Photo.position).all()  # <-- With ordering
    videos = Video.query.order_by(Video.position).all()  # <-- With ordering
    return render_template('gallery.html', title='Gallery', photos=photos, videos=videos)


@app.route('/delete_appointment/<int:appointment_id>', methods=['POST'])
def delete_appointment(appointment_id):
    if 'admin_logged_in' not in session:
        return redirect(url_for('login'))
    appointment = Appointment.query.get_or_404(appointment_id)
    db.session.delete(appointment)
    db.session.commit()
    flash('Appointment has been deleted.', 'success')
    return redirect(url_for('admin'))


@app.route('/delete_photo/<int:photo_id>', methods=['POST'])
def delete_photo(photo_id):
    if 'admin_logged_in' not in session:
        return redirect(url_for('login'))
    photo = Photo.query.get_or_404(photo_id)
    # Also delete the file from the server
    try:
        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], photo.filename))
    except OSError as e:
        flash(f'Error deleting file: {e}', 'danger')
    db.session.delete(photo)
    db.session.commit()
    flash('Photo has been deleted.', 'success')
    return redirect(url_for('admin'))


@app.route('/delete_video/<int:video_id>', methods=['POST'])
def delete_video(video_id):
    if 'admin_logged_in' not in session:
        return redirect(url_for('login'))
    video = Video.query.get_or_404(video_id)
    # Also delete the file from the server
    try:
        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], video.filename))
    except OSError as e:
        flash(f'Error deleting file: {e}', 'danger')
    db.session.delete(video)
    db.session.commit()
    flash('Video has been deleted.', 'success')
    return redirect(url_for('admin'))

# app.py içindeki get_events() fonksiyonunu güncelleyin

@app.route('/api/events')
def get_events():
    if 'admin_logged_in' not in session:
        return jsonify([])

    appointments = Appointment.query.all()
    event_list = []
    for appt in appointments:
        event_list.append({
            'id': appt.id,
            'title': appt.name,
            'start': f"{appt.date}T{appt.time}:00",
            # YENİ: Olayın statüsünü CSS için iletiyoruz
            'extendedProps': {
                'status': appt.status
            }
        })
    return jsonify(event_list)

@app.route('/api/add_event', methods=['POST'])
def add_event():
    if 'admin_logged_in' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401

    data = request.get_json()

    # Gerekli verilerin gelip gelmediğini kontrol et
    if not data.get('date') or not data.get('time') or not data.get('status'):
        return jsonify({'success': False, 'error': 'Missing required fields'}), 400

    # Eğer statü "booked" ise, isim ve telefon zorunlu
    if data['status'] == 'booked' and (not data.get('name') or not data.get('phone')):
        return jsonify({'success': False, 'error': 'Client name and phone are required for bookings'}), 400

    # Eğer statü "blocked" ise, isim ve telefonu standart bir değere ata
    if data['status'] == 'blocked':
        data['name'] = 'Blocked'
        data['phone'] = '-'

    try:
        new_appointment = Appointment(
            name=data['name'],
            phone=data['phone'],
            date=data['date'],
            time=data['time'],
            message='', # Admin eklediği için mesaj boş olabilir
            status=data['status']
        )
        db.session.add(new_appointment)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    

# app.py içinde

@app.route('/api/update_event/<int:event_id>', methods=['POST'])
def update_event(event_id):
    if 'admin_logged_in' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401

    appointment = Appointment.query.get_or_404(event_id)
    data = request.get_json()

    # FullCalendar'dan gelen yeni başlangıç tarihini ve saatini al
    new_start = data.get('start')
    if not new_start:
        return jsonify({'success': False, 'error': 'New start date is required'}), 400

    try:
        # Gelen tarihi (örn: '2025-10-20T14:00:00') ayır
        dt_object = datetime.fromisoformat(new_start)
        appointment.date = dt_object.strftime('%Y-%m-%d')
        appointment.time = dt_object.strftime('%H:%M')

        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/delete_event/<int:event_id>', methods=['POST'])
def delete_event(event_id):
    if 'admin_logged_in' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401

    appointment = Appointment.query.get_or_404(event_id)

    try:
        db.session.delete(appointment)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/available_slots/<string:date>')
def get_available_slots(date):
    try:
        selected_date = datetime.strptime(date, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'Invalid date format'}), 400

    try:
        booked_appointments = Appointment.query.filter_by(date=date).all()
        booked_times = [datetime.strptime(appt.time, '%H:%M').time() for appt in booked_appointments]
    except Exception as e:
        print(f"Database error: {e}")
        return jsonify({'error': 'Could not query database'}), 500

    available_slots = []
    start_time = datetime.strptime(f"{WORKING_HOURS_START}:00", '%H:%M')
    end_time = datetime.strptime(f"{WORKING_HOURS_END}:00", '%H:%M')
    current_time_slot = start_time

    # Türkiye saat dilimini ayarla
    turkey_tz = pytz.timezone('Europe/Istanbul')
    now_in_turkey = datetime.now(turkey_tz)

    while current_time_slot < end_time:
        slot_time = current_time_slot.time()

        # Seçilen tarih ve saati birleştirip saat dilimi bilgisi ekle
        slot_datetime = turkey_tz.localize(datetime.combine(selected_date, slot_time))

        # Eğer o saat dilimi dolu değilse VE geçmişte bir tarih/saat değilse listeye ekle
        if slot_time not in booked_times and slot_datetime > now_in_turkey:
            available_slots.append(slot_time.strftime('%H:%M'))

        current_time_slot += timedelta(minutes=APPOINTMENT_DURATION_MINUTES)

    return jsonify(available_slots)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
