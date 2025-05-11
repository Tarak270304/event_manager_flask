from flask import Flask, render_template, request, redirect, url_for, send_from_directory, jsonify
import os
import sqlite3
import uuid
from werkzeug.utils import secure_filename
import qrcode

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/photos'
app.config['QRCODE_FOLDER'] = 'static/qrcodes'
app.config['DB_PATH'] = 'users.db'

# Ensure required directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['QRCODE_FOLDER'], exist_ok=True)

# Initialize database if needed
def init_db():
    with sqlite3.connect(app.config['DB_PATH']) as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            photo TEXT NOT NULL
        )''')
init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['POST'])
def register():
    name = request.form['name']
    photo = request.files['photo']
    if not name or not photo:
        return "Missing name or photo", 400

    user_id = str(uuid.uuid4())
    filename = secure_filename(f"{user_id}.jpg")
    photo_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    photo.save(photo_path)

    # Save user to database
    with sqlite3.connect(app.config['DB_PATH']) as conn:
        conn.execute("INSERT INTO users (id, name, photo) VALUES (?, ?, ?)", (user_id, name, filename))

    # Generate QR code
    qr_img = qrcode.make(user_id)
    qr_path = os.path.join(app.config['QRCODE_FOLDER'], f"{user_id}.png")
    qr_img.save(qr_path)

    return render_template("qr_display.html", user_id=user_id, qr_image=f"/static/qrcodes/{user_id}.png")

@app.route('/scan/<user_id>')
def scan(user_id):
    with sqlite3.connect(app.config['DB_PATH']) as conn:
        cur = conn.cursor()
        cur.execute("SELECT name, photo FROM users WHERE id = ?", (user_id,))
        result = cur.fetchone()

    if not result:
        return "User not found", 404

    name, photo = result
    return render_template("scan_result.html", name=name, photo_url=f"/static/photos/{photo}")

@app.route("/scan")
def scan_page():
    return render_template("scan.html")

@app.route("/scan-checkin", methods=["POST"])
def scan_checkin():
    data = request.get_json()
    qr_data = data.get("qr_data")

    if qr_data:
        with sqlite3.connect(app.config['DB_PATH']) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM users WHERE id = ?", (qr_data,))
            user = cursor.fetchone()

        if user:
            return jsonify(success=True, user_id=user[0])

    return jsonify(success=False)

if __name__ == '__main__':
    # Run server on all interfaces so mobile device can access it
    app.run(host='0.0.0.0', port=5000, debug=True)


