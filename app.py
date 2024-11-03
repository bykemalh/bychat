from flask import Flask, render_template, request, jsonify, redirect, url_for, session,flash,g, Response,stream_with_context
from werkzeug.security import generate_password_hash, check_password_hash
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText 
from datetime import timedelta, datetime
from flask_sqlalchemy import SQLAlchemy
import google.generativeai as genai
from flask_turnstile import Turnstile
import secrets
import logging
import secrets
import json
import time

app = Flask(__name__)
turnstile = Turnstile(app=app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

app.config.update(
    SESSION_COOKIE_SECURE=False,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
)

app.config.update(dict(
    TURNSTILE_ENABLED = True,
    TURNSTILE_SITE_KEY = "",
    TURNSTILE_SECRET_KEY = ""
))

turnstile = Turnstile()
turnstile.init_app(app)

app.secret_key = 'replace this is'
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    first_name = db.Column(db.String(80), nullable=False)
    last_name = db.Column(db.String(80), nullable=False)
    reset_key = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

class HistoryModel:
    @staticmethod
    def save_history(user_id, token, history):
        # Verileri MariaDB'ye kaydetmek için SQLAlchemy kullanacağız
        for message in history:
            new_history = History(
                user_id=user_id,  # Kullanıcı kimliğini kaydediyoruz
                token=token,
                role=message['role'],
                parts=json.dumps(message['parts'])  # JSON verilerini bir string olarak saklayacağız
            )
            db.session.add(new_history)
        db.session.commit()

    @staticmethod
    def load_history(token):
        history = History.query.filter_by(token=token).all()
        return [{
            'role': message.role,
            'parts': json.loads(message.parts)  # String olarak saklanan JSON verilerini geri yüklüyoruz
        } for message in history]

class History(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)  # Kullanıcı kimliği sütunu
    token = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(10), nullable=False)
    parts = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

class DeletedAccount(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    email = db.Column(db.String(120), nullable=False)
    reason = db.Column(db.String(255), nullable=False)
    deleted_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

def generate_token():
    return secrets.token_hex(8)

with open("data/key.json", "r") as f:
    data = json.load(f)

apiKey = data["apikey"]

genai.configure(api_key=apiKey)

with open("data/config.json", "r") as f:
    generation_config = json.load(f)

with open("data/safety.json", "r") as f:
    safety_settings = json.load(f)

@app.before_request
def log_session_state():
    logging.info(f"Session contents: {dict(session)}")
    logging.info(f"Session permanent: {session.permanent}")

@app.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        # Turnstile doğrulamasını kontrol et
        if not turnstile.verify():
            flash("Recaptcha doğrulaması başarısız oldu. Lütfen tekrar deneyin.", "danger")
            return render_template("forgot_password.html")

        email = request.form.get("email")
        user = User.query.filter_by(email=email).first()
        
        if user:
            reset_key = generate_reset_key()
            user.reset_key = reset_key
            db.session.commit()
            
            send_reset_email(email, reset_key)
            
            flash("Şifre sıfırlama bağlantısı e-posta adresinize gönderildi.", "success")
            return redirect(url_for("forgot_password"))
        else:
            flash("Bu e-posta adresiyle kayıtlı bir kullanıcı bulunamadı.", "danger")

    return render_template("forgot_password.html")

def generate_reset_key():
    return secrets.token_urlsafe(20)

def send_reset_email(email, reset_key):
    sender_email = ""
    receiver_email = email
    password = ""

    message = MIMEMultipart("alternative")
    message["From"] = sender_email
    message["To"] = receiver_email
    message["Subject"] = "Şifre Sıfırlama"

    # E-posta gövdesi için HTML içeriği
    html_body = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; background-color: #f4f4f4; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);">
                <div style="padding: 20px; text-align: center;">
                    <h2 style="color: #333;">Şifre Sıfırlama Talebi</h2>
                    <p style="color: #555;">Merhaba,</p>
                    <p style="color: #555;">
                        Şifrenizi sıfırlamak için aşağıdaki butona tıklayın:
                    </p>
                    <a href="{url_for('reset_password', reset_key=reset_key, _external=True)}" style="display: inline-block; padding: 10px 20px; background-color: #4CAF50; color: #fff; text-decoration: none; border-radius: 4px; margin: 20px 0; font-weight: bold;">
                        Şifreyi Sıfırla
                    </a>
                    <p style="color: #555;">
                        Eğer bu işlemi siz başlatmadıysanız, bu e-postayı görmezden gelebilirsiniz.
                    </p>
                    <p style="color: #555;">Saygılarımızla,</p>
                    <p style="color: #333; font-weight: bold;">Sistem Yönetimi</p>
                </div>
            </div>
        </body>
    </html>
    """

    # HTML gövdeyi e-postaya ekle
    message.attach(MIMEText(html_body, "html"))

    # SMTP bağlantısı başlat ve STARTTLS kullan
    with smtplib.SMTP("mail.", 587) as server:
        server.starttls()  # STARTTLS komutunu çağırarak şifreli bağlantı başlat
        server.login(sender_email, password)
        server.sendmail(sender_email, receiver_email, message.as_string())

@app.route("/reset_password/<reset_key>", methods=["GET", "POST"])
def reset_password(reset_key):
    user = User.query.filter_by(reset_key=reset_key).first()
    if not user:
        flash("Geçersiz veya süresi dolmuş şifre sıfırlama bağlantısı.", "danger")
        return redirect(url_for("login"))
    
    if request.method == "POST":
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")
        if password == confirm_password:
            # Yeni şifreyi hashleyerek kaydet
            user.password = generate_password_hash(password)
            user.reset_key = None
            db.session.commit()
            flash("Şifreniz başarıyla sıfırlandı. Yeni şifrenizle giriş yapabilirsiniz.", "success")
            time.sleep(5)
            return redirect(url_for("login"))
        else:
            flash("Girdiğiniz şifreler eşleşmiyor.", "danger")

    return render_template("reset_password.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("index"))
    
    session.permanent = True

    if request.method == "POST":
        if turnstile.verify():   
            email = request.form.get("email")
            password = request.form.get("password")

            user = User.query.filter_by(email=email).first()
            # Şifre doğrulama
            if user and check_password_hash(user.password, password):
                session["user_id"] = user.id
                return redirect(url_for("index"))
            else:
                return render_template("login.html", error="Invalid email or password")
        else:
            return render_template("login.html", error="Recaptcha Error")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("user_id", None)
    return redirect(url_for("login"))

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if session.get("user_id"):
        return redirect(url_for("index"))

    if request.method == "POST":
        if turnstile.verify():
            email = request.form.get("email")
            password = request.form.get("password")
            first_name = request.form.get("first_name")
            last_name = request.form.get("last_name")

            existing_user = User.query.filter_by(email=email).first()
            if existing_user:
                return render_template("signup.html", error="Email is already in use")

            # Şifreyi hashleyerek kaydet
            hashed_password = generate_password_hash(password)
            new_user = User(email=email, password=hashed_password, first_name=first_name, last_name=last_name)
            db.session.add(new_user)
            db.session.commit()
            return redirect(url_for("login"))
        else:
            return render_template("signup.html", error="reCaptcha Error")

    return render_template("signup.html")

@app.errorhandler(404)
def not_found(error):
    return render_template('hata.html'), 404

@app.route("/account", methods=["GET", "POST"])
def account():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]
    user = db.session.get(User, session["user_id"])

    if request.method == "POST":
        if turnstile.verify():
            user.email = request.form.get("email")
            user.first_name = request.form.get("first_name")
            user.last_name = request.form.get("last_name")
            db.session.commit()
        else:
            return render_template("signup.html", error="reCaptcha Error")

        return redirect(url_for("index"))

    return render_template("account.html", user=user)

@app.route("/account/delete", methods=["GET", "POST"])
def delete_account():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user = User.query.get(session["user_id"])

    if request.method == "POST":
        reason = request.form.get("reason")

        # Hesap silme nedenini veritabanında kaydet
        deleted_account = DeletedAccount(user_id=user.id, email=user.email, reason=reason)
        db.session.add(deleted_account)
        db.session.delete(user)  # Hesabı sil
        db.session.commit()
        
        session.clear()  # Hesap silindiği için oturumu temizle
        return redirect(url_for("index"))

    return render_template("delete.html", user=user)


@app.route("/")
def index():
    if "user_id" not in session:
        return render_template("welcome.html")
    
    user = db.session.get(User, session["user_id"])
    token = generate_token()
    session['current_token'] = token  # Token'ı oturuma kaydet
    user_id = session["user_id"]
    user_histories = {}

    # Kullanıcının geçmişini veritabanından çek
    user_histories = {}  # Kullanıcının geçmişlerini depolamak için bir sözlük
    histories = History.query.filter_by(user_id=user_id).all()

    for history in histories:
        if history.token not in user_histories:
            user_histories[history.token] = []

        user_histories[history.token].append(history.parts)

    return render_template("index.html", user=user, token=token,user_histories=user_histories)

@app.route("/history")
def history():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]
    user_histories = {}

    # Kullanıcının geçmişini veritabanından çek
    user_histories = {}  # Kullanıcının geçmişlerini depolamak için bir sözlük
    histories = History.query.filter_by(user_id=user_id).all()

    for history in histories:
        if history.token not in user_histories:
            user_histories[history.token] = []

        user_histories[history.token].append(history.parts)

    return render_template("history.html", user_histories=user_histories)

@app.route("/load_history", methods=["POST"])
def load_history():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.get_json()
    token = data.get('token')
    
    history = HistoryModel.load_history(token)
    return jsonify({"history": history})

@app.route('/chat', methods=['POST'])
def chat():
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    data = request.get_json()
    prompt = data['prompt']
    token = data['token']
    user_id = session["user_id"]
    
    history = HistoryModel.load_history(token)

    model = genai.GenerativeModel(
        model_name="tunedModels/bychatpro-f72w11962b0t",
        generation_config=generation_config,
        safety_settings=safety_settings
    )
    
    convo = model.start_chat(history=history)
    
    def generate():
        response = convo.send_message(prompt, stream=True)
        full_response = ""
        for chunk in response:
            if chunk.text:
                full_response += chunk.text
                yield json.dumps({"chunk": chunk.text}) + "\n"
        
        HistoryModel.save_history(user_id, token, [
            {"role": "user", "parts": prompt},
            {"role": "model", "parts": [full_response]}
        ])
    
    return Response(stream_with_context(generate()), content_type='application/json')

@app.route("/user-agreement")
def user_agreement():
    return render_template("user_agreement.html")

@app.route("/terms-of-service")
def terms_of_service():
    return render_template("terms_of_service.html")

@app.route("/help")
def help_page():
    return render_template("help.html")

@app.route("/release-notes")
def release_notes():
    return render_template("release_notes.html")

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    logging.basicConfig(level=logging.DEBUG)
    app.run(host='0.0.0.0',debug=True, port=5000)