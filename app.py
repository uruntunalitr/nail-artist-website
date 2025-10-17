from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from werkzeug.utils import secure_filename
import os
from forms import AppointmentForm, PhotoUploadForm, VideoUploadForm, LoginForm, AddServiceForm
from datetime import datetime, timedelta
import pytz,math

app = Flask(__name__)
# IMPORTANT: Change this secret key!
app.config['SECRET_KEY'] = 'a_very_secret_key_change_it'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
db = SQLAlchemy(app)

WORKING_HOURS_START = 9  # Sabah 9
WORKING_HOURS_END = 18   # Akşam 6 (18:00'e kadar çalışılıyor, 18:00 randevu değil)
APPOINTMENT_DURATION_MINUTES = 60 # Her randevu 60 dakika sürer

app.config['MAIL_SERVER'] = 'smtp.googlemail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'uruntunali@gmail.com'
app.config['MAIL_PASSWORD'] = 'gwyx wupi hmxt ubtb'
mail = Mail(app)

# --- Database Models ---


class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=True)
    phone = db.Column(db.String(20), nullable=False)
    date = db.Column(db.String(20), nullable=False)
    time = db.Column(db.String(10), nullable=False)
    message = db.Column(db.Text, nullable=True)

    # 'status' güncellendi: 'pending', 'confirmed', 'blocked'
    status = db.Column(db.String(20), nullable=False, default='pending') 

    # 'duration' kaldırıldı, yerine hizmete bağlantı eklendi
    service_id = db.Column(db.Integer, db.ForeignKey('service.id'), nullable=True) 

    # Hizmet bilgisine kolay erişim için
    service = db.relationship('Service', backref=db.backref('appointments', lazy=True))

class Service(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    duration = db.Column(db.Integer, nullable=False, default=60) # Süre (dakika)
    position = db.Column(db.Integer, nullable=False, default=100)

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


# app.py içindeki book() fonksiyonunu bulun
# app.py içindeki book() fonksiyonunu bununla değiştirin

@app.route('/book', methods=['GET', 'POST'])
def book():
    form = AppointmentForm()
    
    # Hizmet listesini her zaman doldur (GET ve POST için)
    form.service.choices = [
        (s.id, f"{s.name} ({s.duration} min)") 
        for s in Service.query.order_by(Service.position).all()
    ]

    # --- YENİ EKLENEN BÖLÜM BAŞLANGICI ---
    # Eğer form gönderildiyse (POST), doğrulama yapmadan önce o tarihe ait
    # müsait saatleri hesaplayıp formun time.choices listesini doldurmamız gerekir.
    if request.method == 'POST':
        try:
            service_id = int(request.form.get('service'))
            date_str = request.form.get('date')
            
            if service_id and date_str:
                selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                service = Service.query.get(service_id)
                new_appt_duration = service.duration

                # get_available_slots fonksiyonundaki mantığın aynısını burada çalıştır
                appointments_today = Appointment.query.filter_by(date=date_str).all()
                blocked_slots = set()
                for appt in appointments_today:
                    start_time = datetime.strptime(appt.time, '%H:%M')
                    duration = appt.service.duration if appt.service else 60
                    slots_needed = math.ceil(duration / APPOINTMENT_DURATION_MINUTES)
                    for i in range(slots_needed):
                        slot_time = (start_time + timedelta(minutes=i * APPOINTMENT_DURATION_MINUTES)).time()
                        blocked_slots.add(slot_time)

                available_slots = []
                turkey_tz = pytz.timezone('Europe/Istanbul')
                now_in_turkey = datetime.now(turkey_tz)
                start_of_day = datetime.strptime(f"{WORKING_HOURS_START}:00", '%H:%M')
                end_of_day = datetime.strptime(f"{WORKING_HOURS_END}:00", '%H:%M')
                current_slot = start_of_day

                while current_slot < end_of_day:
                    slot_time = current_slot.time()
                    slot_datetime = turkey_tz.localize(datetime.combine(selected_date, slot_time))
                    if slot_time not in blocked_slots and slot_datetime > now_in_turkey:
                        is_slot_available = True
                        slots_needed_for_new = math.ceil(new_appt_duration / APPOINTMENT_DURATION_MINUTES)
                        for i in range(slots_needed_for_new):
                            time_to_check = (current_slot + timedelta(minutes=i * APPOINTMENT_DURATION_MINUTES)).time()
                            end_time_to_check = (current_slot + timedelta(minutes=i * APPOINTMENT_DURATION_MINUTES))
                            if time_to_check in blocked_slots or end_time_to_check >= end_of_day:
                                is_slot_available = False
                                break
                        if is_slot_available:
                            available_slots.append(slot_time.strftime('%H:%M'))
                    current_slot += timedelta(minutes=APPOINTMENT_DURATION_MINUTES)
                
                # Formun saat seçeneklerini bu müsait saatlerle doldur
                form.time.choices = [(slot, slot) for slot in available_slots]
        except Exception as e:
            print(f"Error populating time choices on POST: {e}")
            form.time.choices = []
    # --- YENİ EKLENEN BÖLÜM SONU ---


    if form.validate_on_submit():
        # Buradaki GÜVENLİK KONTROLÜ (Flash mesajı veren) zaten doğru çalışıyor
        # ... (mevcut güvenlik kontrolü ve randevu kaydetme kodunuz) ...
        # ...
        date_str = form.date.data.strftime('%Y-%m-%d')
        time_str = form.time.data
        selected_date = form.date.data
        
        # Seçilen hizmetin süresini al
        service = Service.query.get(form.service.data)
        if not service:
            flash('Selected service not found.', 'danger')
            return render_template('book.html', title='Book Appointment', form=form)
        new_appt_duration = service.duration

        # --- GÜVENLİK KONTROLÜ (DÜZELTİLMİŞ HALİ) ---
        appointments_today = Appointment.query.filter_by(date=date_str).all()
        blocked_slots = set()
        for appt in appointments_today:
            start_time = datetime.strptime(appt.time, '%H:%M')
            duration = appt.service.duration if appt.service else 60
            
            slots_needed = math.ceil(duration / APPOINTMENT_DURATION_MINUTES)
            
            for i in range(slots_needed):
                slot_time = (start_time + timedelta(minutes=i * APPOINTMENT_DURATION_MINUTES)).time()
                blocked_slots.add(slot_time)
        
        selected_time_obj = datetime.strptime(time_str, '%H:%M')
        slots_needed_for_new = math.ceil(new_appt_duration / APPOINTMENT_DURATION_MINUTES)
        
        is_safe_to_book = True
        for i in range(slots_needed_for_new):
            time_to_check = (selected_time_obj + timedelta(minutes=i * APPOINTMENT_DURATION_MINUTES)).time()
            if time_to_check in blocked_slots:
                is_safe_to_book = False
                break
        
        if not is_safe_to_book:
            flash('The selected time is no longer available or conflicts with another appointment. Please choose another time.', 'danger')
            return render_template('book.html', title='Book Appointment', form=form)
        # --- GÜVENLİK KONTROLÜ SONU ---

        
        # Randevuyu 'pending' olarak kaydet
        new_appointment = Appointment(
            name=form.name.data,
            email=form.email.data,
            phone=form.phone.data,
            date=date_str,
            time=time_str,
            service_id=form.service.data,
            message=form.message.data,
            status='pending'
        )
        db.session.add(new_appointment)
        db.session.commit()
            
        flash('Your appointment request has been sent! You will receive an email upon confirmation.', 'success')
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
    service_form = AddServiceForm() 


    if service_form.submit_service.data and service_form.validate_on_submit():
        new_service = Service(
            name=service_form.name.data,
            duration=service_form.duration.data
        )
        db.session.add(new_service)
        db.session.commit()
        flash('Service added successfully!', 'success')
        return redirect(url_for('admin'))

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
    services = Service.query.order_by(Service.position).all()

    return render_template('admin.html', title='Admin Panel',
                           appointments=appointments, photos=photos, videos=videos, services=services, 
                           photo_form=photo_form, video_form=video_form, service_form=service_form)

@app.route('/delete_service/<int:service_id>', methods=['POST'])
def delete_service(service_id):
    if 'admin_logged_in' not in session:
        return redirect(url_for('login'))
    service = Service.query.get_or_404(service_id)
    db.session.delete(service)
    db.session.commit()
    flash('Service has been deleted.', 'success')
    return redirect(url_for('admin'))

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
        start_datetime = datetime.strptime(f"{appt.date}T{appt.time}:00", "%Y-%m-%dT%H:%M:%S")
        # Hizmetin süresini al, eğer hizmet silinmişse 60dk varsay
        duration = appt.service.duration if appt.service else 60
        end_datetime = start_datetime + timedelta(minutes=duration)

        event_list.append({
            'id': appt.id,
            'title': appt.name,
            'start': start_datetime.isoformat(),
            'end': end_datetime.isoformat(),
            'extendedProps': {
                'status': appt.status,
                'phone': appt.phone,
                'message': appt.message,
                'date': appt.date,
                'time': appt.time,
                'email': appt.email, # E-postayı da gönderelim
                'service_name': appt.service.name if appt.service else 'N/A'
            }
        })
    return jsonify(event_list)

@app.route('/api/approve_appointment/<int:appointment_id>', methods=['POST'])
def approve_appointment(appointment_id):
    if 'admin_logged_in' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401

    appointment = Appointment.query.get_or_404(appointment_id)

    try:
        # Randevunun statüsünü 'confirmed' yap
        appointment.status = 'confirmed'
        db.session.commit()

        # Müşteriye onay e-postası gönder
        msg = Message('Your Appointment is Confirmed!',
                      sender=app.config['MAIL_USERNAME'],
                      recipients=[appointment.email])
        msg.body = f"""
        Hi {appointment.name},

        Your appointment for {appointment.service.name} on {appointment.date} at {appointment.time} has been confirmed!

        See you soon!
        - Funda Turalı Nail Artist
        """
        mail.send(msg)

        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


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
            status=data['status'],
            email=data.get('email', None), # BU SATIRI EKLEYİN
            service_id=None if data['status'] == 'blocked' else data.get('service_id', None)
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


# app.py içindeki get_available_slots fonksiyonunu bununla değiştirin

@app.route('/api/available_slots/<int:service_id>/<string:date>')
def get_available_slots(service_id, date):
    try:
        selected_date = datetime.strptime(date, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'Invalid date format'}), 400
    
    service = Service.query.get(service_id)
    if not service:
        return jsonify({'error': 'Service not found'}), 404
    new_appt_duration = service.duration
    
    # Adım 1: O günkü tüm dolu aralıkları (slot) hesapla
    appointments_today = Appointment.query.filter_by(date=date).all()
    blocked_slots = set()
    for appt in appointments_today:
        start_time = datetime.strptime(appt.time, '%H:%M')
        duration = appt.service.duration if appt.service else 60
        
        # DÜZELTME: Gerekli slot sayısını 'math.ceil' ile hesapla
        slots_needed = math.ceil(duration / APPOINTMENT_DURATION_MINUTES)
        
        for i in range(slots_needed):
            slot_time = (start_time + timedelta(minutes=i * APPOINTMENT_DURATION_MINUTES)).time()
            blocked_slots.add(slot_time)

    # Adım 2: Müsait saatleri bul
    available_slots = []
    turkey_tz = pytz.timezone('Europe/Istanbul')
    now_in_turkey = datetime.now(turkey_tz)
    
    start_of_day = datetime.strptime(f"{WORKING_HOURS_START}:00", '%H:%M')
    end_of_day = datetime.strptime(f"{WORKING_HOURS_END}:00", '%H:%M')
    
    current_slot = start_of_day
    while current_slot < end_of_day:
        slot_time = current_slot.time()
        slot_datetime = turkey_tz.localize(datetime.combine(selected_date, slot_time))

        if slot_time not in blocked_slots and slot_datetime > now_in_turkey:
            # Randevunun sığıp sığmadığını kontrol et
            is_slot_available = True
            # DÜZELTME: Gerekli slot sayısını 'math.ceil' ile hesapla
            slots_needed_for_new = math.ceil(new_appt_duration / APPOINTMENT_DURATION_MINUTES)
            
            for i in range(slots_needed_for_new):
                time_to_check = (current_slot + timedelta(minutes=i * APPOINTMENT_DURATION_MINUTES)).time()
                end_time_to_check = (current_slot + timedelta(minutes=i * APPOINTMENT_DURATION_MINUTES))
                
                if time_to_check in blocked_slots or end_time_to_check >= end_of_day:
                    is_slot_available = False
                    break
            
            if is_slot_available:
                available_slots.append(slot_time.strftime('%H:%M'))
        
        current_slot += timedelta(minutes=APPOINTMENT_DURATION_MINUTES)

    return jsonify(available_slots)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
