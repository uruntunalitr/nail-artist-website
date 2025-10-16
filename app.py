from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import os
from forms import AppointmentForm, PhotoUploadForm, VideoUploadForm, LoginForm

app = Flask(__name__)
# IMPORTANT: Change this secret key!
app.config['SECRET_KEY'] = 'a_very_secret_key_change_it'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
db = SQLAlchemy(app)

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
    if form.validate_on_submit():
        new_appointment = Appointment(
            name=form.name.data,
            phone=form.phone.data,
            date=form.date.data.strftime('%Y-%m-%d'),
            time=form.time.data.strftime('%H:%M'),
            message=form.message.data,
            status='booked'  # <-- BU SATIRI EKLEYİN
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

@app.route('/api/events')
def get_events():
    if 'admin_logged_in' not in session:
        return jsonify([]) # Giriş yapılmamışsa boş liste döndür

    appointments = Appointment.query.all()
    event_list = []
    for appt in appointments:
        event_list.append({
            'id': appt.id,
            'title': f"{appt.name} ({appt.time})",
            'start': f"{appt.date}T{appt.time}:00",
            'backgroundColor': '#EACCD1' if appt.status == 'booked' else '#808080', # Müşteri randevusu pembe, bloklu gri
            'borderColor': '#EACCD1' if appt.status == 'booked' else '#808080'
        })
    return jsonify(event_list)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
