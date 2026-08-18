import os
import re
import json
import random
import requests
from datetime import datetime, date, timedelta, timezone
from functools import wraps

from flask import Flask, render_template, render_template_string, request, redirect, url_for, flash, abort, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from jinja2 import DictLoader
from PIL import Image
from flask_talisman import Talisman
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from models import db, User, News, Manga, Room, Post, Title, UserTitle, Achievement, UserAchievement, Notification, Quest, UserQuest, Report, NewsBlock, NewsLike
from content_generator import generate_news_content, generate_manga_content, get_image_url, fetch_and_generate_news, generate_listicle

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'gizli-acar-12345')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 8 * 1024 * 1024  # 8 MB

db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Zəhmət olmasa giriş edin.'
@login_manager.unauthorized_handler
def unauthorized():
    flash('Zəhmət olmasa giriş edin.')
    return redirect(url_for('index'))

Talisman(app, content_security_policy=None, force_https=False)
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
@app.before_request
def check_banned_user():
    if current_user.is_authenticated:
        if current_user.is_banned:
            if current_user.banned_until and current_user.banned_until < datetime.now():
                # Ban müddəti bitib, azad et
                current_user.is_banned = False
                current_user.banned_until = None
                current_user.banned_reason = ''
                db.session.commit()
            else:
                logout_user()
                flash('Hesabınız banlandı. Səbəb: ' + (current_user.banned_reason or 'Göstərilməyib'))
                return redirect(url_for('index'))
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

def is_strong_password(password):
    if len(password) < 8:
        return False
    if not any(c.isalpha() for c in password):
        return False
    if not any(c.isdigit() for c in password):
        return False
    return True

def add_notification(user, message):
    if not user:
        return
    notif = Notification(user_id=user.id, message=message)
    db.session.add(notif)
    db.session.commit()

def daily_reward(user):
    if user.is_admin:
        return False
    today = date.today().isoformat()
    if user.last_login_date == today:
        return False
    if user.last_login_date == (date.today() - timedelta(days=1)).isoformat():
        user.streak += 1
    else:
        user.streak = 1
    bonus = 10 + (user.streak - 1) * 5
    user.points += bonus
    user.last_login_date = today
    db.session.commit()
    update_quest_progress(user, 'daily_login', 1)
    update_quest_progress(user, 'points', bonus)
    check_achievements(user)
    update_user_title(user)
    add_notification(user, f"Günlük giriş ödülü: +{bonus} XP")
    return True

def can_increment_view(obj_id):
    key = f"viewed_{obj_id}"
    last_view = session.get(key)
    now = datetime.now().timestamp()
    if last_view is None or (now - last_view) > 60:
        session[key] = now
        return True
    return False

def process_image(file, max_width, max_height):
    if not file:
        return None
    try:
        ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else 'jpg'
        if ext not in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
            return None
        img = Image.open(file)
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
        width, height = img.size
        if width / height > max_width / max_height:
            new_width = int(height * max_width / max_height)
            left = (width - new_width) // 2
            right = left + new_width
            img = img.crop((left, 0, right, height))
        else:
            new_height = int(width * max_height / max_width)
            top = (height - new_height) // 2
            bottom = top + new_height
            img = img.crop((0, top, width, bottom))
        img = img.resize((max_width, max_height), Image.Resampling.LANCZOS)
        filename = f"upload_{datetime.utcnow().timestamp()}_{random.randint(1000,9999)}.jpg"
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        img.save(save_path, "JPEG", quality=85)
        return filename
    except Exception as e:
        print(f"Şəkil emalı xətası: {e}")
        return None

# ---------- Bonus hesablanması ----------
def get_bonus_percent(user):
    if user.is_admin:
        return 100
    if user.title:
        color = user.title.color
        if color == 'white':
            return 5
        elif color == 'green':
            return 10
        elif color == 'blue':
            return 20
        elif color == 'purple':
            return 35
        elif color == 'yellow':
            return 50
        elif color == 'red':
            return 100
    return 0

def add_xp(user, amount):
    update_user_title(user)
    if user.is_admin:
        return 0
    bonus_percent = get_bonus_percent(user)
    total = amount + int(amount * bonus_percent / 100)
    if total == 0:
        total = 1
    user.points += total
    db.session.commit()
    update_user_title(user)
    return total

# ---------- Ünvan sisteminin yenilənməsi ----------
def seed_titles():
    if Title.query.count() > 0:
        return
    # Ağ (20)
    white_titles = [
        ("Başlanğıc", "İlk addım"),
        ("İlk Addım", "Saytda ilk fəaliyyət"),
        ("Oxucu", "İlk xəbəri oxu"),
        ("İzləyici", "İlk manqa/animeni izlə"),
        ("Maraqlı", "5 xəbər oxu"),
        ("Naşı", "10 XP topla"),
        ("Pərəstişkar", "3 gün ardıcıl giriş"),
        ("Sadiq", "7 gün ardıcıl giriş"),
        ("Aktiv", "5 şərh yaz"),
        ("Daimi", "10 şərh yaz"),
        ("Gənc Qəhrəman", "25 bəyənmə et"),
        ("Tədqiqatçı", "3 müxtəlif otaqda şərh yaz"),
        ("Səyyah", "5 müxtəlif otaqda şərh yaz"),
        ("Müşahidəçi", "10 xəbər oxu"),
        ("Nağılçı", "1 müzakirə otağı yarat"),
        ("Yolçu", "20 xəbər oxu"),
        ("Kəşfiyyatçı", "50 bəyənmə et"),
        ("Dost", "2 nailiyyət qazan"),
        ("İlk Vitrin", "İlk ünvanı vitrinə əlavə et"),
        ("Sadiq Oxucu", "30 xəbər oxu"),
    ]
    # Yaşıl (18)
    green_titles = [
        ("Təcrübəli", "100 XP topla"),
        ("Bilikli", "50 xəbər oxu"),
        ("Sürətli", "3 günlük giriş seriyası"),
        ("Çevik", "7 günlük giriş seriyası"),
        ("Usta Tələbə", "100 bəyənmə et"),
        ("Gizli Gəzən", "10 müxtəlif otaqda şərh yaz"),
        ("Anime Ovçusu", "5 anime manqası oxu"),
        ("Manhwa Kəşfiyyatçısı", "5 manhwa oxu"),
        ("Manga Bilici", "5 manga oxu"),
        ("Webtoon Həvəskarı", "5 webtoon oxu"),
        ("Səhnə Ustası", "5 müzakirə otağı yarat"),
        ("Döyüşçü", "200 XP topla"),
        ("Sadiq İzləyici", "14 günlük giriş seriyası"),
        ("Səsli", "50 şərh yaz"),
        ("İnamlı", "300 XP topla"),
        ("Canlı", "100 xəbər oxu"),
        ("Ulduz", "3 nailiyyət qazan"),
        ("Veteran", "400 XP topla"),
    ]
    # Mavi (16)
    blue_titles = [
        ("Usta", "500 XP topla"),
        ("Veteran", "700 XP topla"),
        ("Strateq", "300 bəyənmə et"),
        ("Döyüşçü", "30 günlük giriş seriyası"),
        ("Əfsanəvi Ovçu", "20 müxtəlif otaqda şərh yaz"),
        ("Qaranlıq Cəngavər", "1000 XP topla"),
        ("Neon Qılınc", "1500 XP topla"),
        ("Səviyyə Atıcısı", "10 nailiyyət qazan"),
        ("Manhva Lordu", "50 manhwa oxu"),
        ("Anime Senpaysı", "50 anime izlə"),
        ("Manga Həkimi", "50 manga oxu"),
        ("Webtoon Ustası", "50 webtoon oxu"),
        ("Sadiq Müzakirəçi", "20 müzakirə otağı yarat"),
        ("Səs Kralı", "200 şərh yaz"),
        ("Xəbər Canavarı", "200 xəbər oxu"),
        ("İşıq Sürəti", "500 bəyənmə et"),
    ]
    # Bənövşəyi (12) - gizli, xüsusi şərtlər
    purple_titles = [
        ("Epik Qəhrəman", "3000 XP + 50 xəbər + 5 nailiyyət", "purple", True, "xp", 3000),
        ("Əfsanəvi Gözətçi", "3500 XP + 100 xəbər + 7 nailiyyət", "purple", True, "xp", 3500),
        ("Buz Döyüşçüsü", "4000 XP + 20 müxtəlif otaqda şərh", "purple", True, "xp", 4000),
        ("Alov Ruhu", "4500 XP + 30 günlük seriya", "purple", True, "xp", 4500),
        ("Kölgə Ustası", "5000 XP + 150 xəbər", "purple", True, "xp", 5000),
        ("Səma Pərəstişkarı", "5500 XP + 10 müzakirə otağı", "purple", True, "xp", 5500),
        ("Titan", "6000 XP + 500 bəyənmə", "purple", True, "xp", 6000),
        ("Dərviş", "6500 XP + 30 nailiyyət", "purple", True, "xp", 6500),
        ("Fırtına Çağıran", "7000 XP + 300 xəbər", "purple", True, "xp", 7000),
        ("Zamansız", "7500 XP + 40 günlük seriya", "purple", True, "xp", 7500),
        ("Ölümsüz", "8000 XP + 600 bəyənmə", "purple", True, "xp", 8000),
        ("Kosmik Səyyah", "8500 XP + 100 müxtəlif otaqda şərh", "purple", True, "xp", 8500),
    ]
    # Sarı (7) - əfsanəvi, hər biri yalnız bir nəfərə
    legendary_titles = [
        ("İlk Toxum", "10000 XP + 100 günlük seriya + 10 nailiyyət + 200 xəbər + 100 bəyənmə", "yellow", True, "xp", 10000),
        ("Tanrı Səviyyəsi", "12000 XP + 120 günlük seriya + 12 nailiyyət + 300 xəbər + 200 bəyənmə", "yellow", True, "xp", 12000),
        ("Mütləq Güc", "14000 XP + 150 günlük seriya + 15 nailiyyət + 500 xəbər + 500 bəyənmə", "yellow", True, "xp", 14000),
        ("Kainat Hökmdarı", "16000 XP + 180 günlük seriya + 20 nailiyyət + 800 xəbər + 1000 bəyənmə", "yellow", True, "xp", 16000),
        ("Son Ümid", "18000 XP + 200 günlük seriya + 25 nailiyyət + 1000 xəbər + 2000 bəyənmə", "yellow", True, "xp", 18000),
        ("Əbədi Əfsanə", "20000 XP + 250 günlük seriya + 30 nailiyyət + 1500 xəbər + 5000 bəyənmə", "yellow", True, "xp", 20000),
        ("İlk Toxum (Alternativ)", "Əsl əfsanə", "yellow", True, "xp", 99999),  # ehtiyat
    ]
    all_titles = []
    for name, desc in white_titles:
        all_titles.append(Title(name=name, description=desc, color="white", rarity="common", hidden=False, condition_type="xp", condition_value=0))
    for name, desc in green_titles:
        all_titles.append(Title(name=name, description=desc, color="green", rarity="uncommon", hidden=False, condition_type="xp", condition_value=0))
    for name, desc in blue_titles:
        all_titles.append(Title(name=name, description=desc, color="blue", rarity="rare", hidden=False, condition_type="xp", condition_value=0))
    for item in purple_titles:
        name = item[0]
        desc = item[1]
        color = item[2]
        hidden = item[3]
        ctype = item[4]
        cvalue = item[5]
        all_titles.append(Title(name=name, description=desc, color=color, rarity="epic", hidden=True, condition_type="xp", condition_value=cvalue))
    for item in legendary_titles:
        name = item[0]
        desc = item[1]
        color = item[2]
        hidden = item[3]
        ctype = item[4]
        cvalue = item[5]
        all_titles.append(Title(name=name, description=desc, color=color, rarity="legendary", hidden=True, condition_type="xp", condition_value=cvalue, unique_legendary=True))

    # Admin ünvanı
    all_titles.append(Title(name="Admin", description="Sayt rəhbəri", color="red", rarity="admin", hidden=False, condition_type="admin", condition_value=0))
    db.session.add_all(all_titles)
    db.session.commit()

def seed_quests_and_achievements():
    if Quest.query.count() == 0:
        quests = [
            Quest(name="Gündəlik Oxucu", description="1 xəbər oxu", requirement_type="news_read", target_value=1, reward_xp=10, is_daily=True),
            Quest(name="Gündəlik Bəyənən", description="1 bəyənmə et", requirement_type="like", target_value=1, reward_xp=5, is_daily=True),
            Quest(name="Gündəlik Şərhçi", description="1 şərh yaz", requirement_type="post", target_value=1, reward_xp=10, is_daily=True),
            Quest(name="Həftəlik Məhsuldar", description="5 xəbər oxu", requirement_type="news_read", target_value=5, reward_xp=30, is_weekly=True),
            Quest(name="Həftəlik Bəyənən", description="5 bəyənmə et", requirement_type="like", target_value=5, reward_xp=20, is_weekly=True),
            Quest(name="Həftəlik Sosial", description="1 müzakirə otağı yarat", requirement_type="room_create", target_value=1, reward_xp=25, is_weekly=True),
        ]
        db.session.add_all(quests)

    if Achievement.query.count() == 0:
        achievements = [
            Achievement(name="İlk Addım", description="İlk xəbəri oxu", badge_icon="📰", requirement_type="news_read", requirement_value=1),
            Achievement(name="Xəbər Canavarı", description="10 xəbər oxu", badge_icon="📚", requirement_type="news_read", requirement_value=10),
            Achievement(name="Bəyənmə Ustası", description="5 bəyənmə et", badge_icon="❤️", requirement_type="like", requirement_value=5),
            Achievement(name="Şərh Mütəxəssisi", description="5 şərh yaz", badge_icon="💬", requirement_type="post", requirement_value=5),
            Achievement(name="Otaq Qurucusu", description="3 müzakirə otağı yarat", badge_icon="🏠", requirement_type="room_create", requirement_value=3),
            Achievement(name="Gündəlik Asılılıq", description="7 gün ardıcıl giriş", badge_icon="🔥", requirement_type="streak", requirement_value=7),
            Achievement(name="Səssiz Qəhrəman", description="50 XP topla", badge_icon="🤫", requirement_type="points", requirement_value=50, hidden=True),
            Achievement(name="Əfsanəvi Kolleksiyaçı", description="100 XP topla", badge_icon="🌟", requirement_type="points", requirement_value=100, hidden=True),
        ]
        db.session.add_all(achievements)
    db.session.commit()

def reset_user_quests(user):
    today = date.today().isoformat()
    for uq in user.quests:
        if uq.quest.is_daily and uq.last_reset_date != today:
            uq.progress = 0
            uq.completed = False
            uq.last_reset_date = today
        elif uq.quest.is_weekly:
            week_start = (date.today() - timedelta(days=date.today().weekday())).isoformat()
            if uq.last_reset_date != week_start:
                uq.progress = 0
                uq.completed = False
                uq.last_reset_date = week_start
    db.session.commit()

def update_quest_progress(user, action_type, amount=1):
    if user.is_admin:
        return
    if not user.is_authenticated:
        return
    reset_user_quests(user)
    quests = Quest.query.filter((Quest.is_daily == True) | (Quest.is_weekly == True)).all()
    for quest in quests:
        if quest.requirement_type != action_type:
            continue
        user_quest = UserQuest.query.filter_by(user_id=user.id, quest_id=quest.id).first()
        if not user_quest:
            user_quest = UserQuest(user_id=user.id, quest_id=quest.id, progress=0, completed=False, last_reset_date=date.today().isoformat())
            db.session.add(user_quest)
            db.session.commit()
        if user_quest.completed:
            continue
        user_quest.progress += amount
        if user_quest.progress >= quest.target_value:
            user_quest.progress = quest.target_value
            user_quest.completed = True
            earned_xp = add_xp(user, quest.reward_xp)
            add_notification(user, f"Görəvi tamamladın: {quest.name} (+{earned_xp} XP)")
        db.session.commit()

def check_achievements(user):
    if user.is_admin:
        return
    if not user.is_authenticated:
        return
    achievements = Achievement.query.all()
    for ach in achievements:
        if UserAchievement.query.filter_by(user_id=user.id, achievement_id=ach.id).first():
            continue
        earned = False
        if ach.requirement_type == 'news_read':
            earned = user.news_read_count >= ach.requirement_value
        elif ach.requirement_type == 'like':
            earned = user.likes_count >= ach.requirement_value
        elif ach.requirement_type == 'post':
            posts_count = Post.query.filter_by(user_id=user.id).count()
            earned = posts_count >= ach.requirement_value
        elif ach.requirement_type == 'room_create':
            rooms_count = Room.query.filter_by(creator_id=user.id).count()
            earned = rooms_count >= ach.requirement_value
        elif ach.requirement_type == 'streak':
            earned = user.streak >= ach.requirement_value
        elif ach.requirement_type == 'points':
            earned = user.points >= ach.requirement_value
        if earned:
            ua = UserAchievement(user_id=user.id, achievement_id=ach.id)
            db.session.add(ua)
            add_notification(user, f"Nailiyyət qazandın: {ach.name} {ach.badge_icon}")
    db.session.commit()

def update_user_title(user):
    if not user:
        return
    if user.is_admin:
        admin_title = Title.query.filter_by(name="Admin").first()
        if admin_title and user.title_id != admin_title.id:
            user.title_id = admin_title.id
            db.session.commit()
        return

    # Qeyri-gizli ünvanları XP-yə görə sırala
    normal_titles = Title.query.filter_by(hidden=False).order_by(Title.required_xp.desc()).all()
    for title in normal_titles:
        if title.rarity in ('common', 'uncommon', 'rare'):
            if user.points >= title.required_xp:
                # Uyğun ünvanı qazanmadısa əlavə et
                if not UserTitle.query.filter_by(user_id=user.id, title_id=title.id).first():
                    user_title = UserTitle(user_id=user.id, title_id=title.id)
                    db.session.add(user_title)
                    db.session.commit()
                    add_notification(user, f"Yeni ünvan qazandın: {title.name}")
                # Aktiv ünvana təyin et (ən yüksək)
                if user.title_id != title.id:
                    user.title_id = title.id
                    db.session.commit()
                break

    # Gizli Epik ünvanlar üçün şərtlər (sadələşdirilmiş: yalnız XP + bəzi şərtlər)
    epic_titles = Title.query.filter_by(rarity="epic", hidden=True).all()
    for title in epic_titles:
        if UserTitle.query.filter_by(user_id=user.id, title_id=title.id).first():
            continue
        # Müvəqqəti sadə şərt: XP-yə görə
        if user.points >= title.condition_value:
            user_title = UserTitle(user_id=user.id, title_id=title.id)
            db.session.add(user_title)
            db.session.commit()
            add_notification(user, f"Epik ünvan qazandın: {title.name}")
            if user.title_id != title.id:
                user.title_id = title.id
                db.session.commit()

    # Əfsanəvi ünvanlar (unique)
    legendaries = Title.query.filter_by(rarity="legendary", hidden=True).all()
    for title in legendaries:
        if UserTitle.query.filter_by(user_id=user.id, title_id=title.id).first():
            continue
        # Əgər başqası alıbsa, keç
        if title.unique_legendary and UserTitle.query.filter_by(title_id=title.id).first():
            continue
        # Şərtlər (sadələşdirilmiş)
        if (user.points >= title.condition_value and user.streak >= 100):
            user_title = UserTitle(user_id=user.id, title_id=title.id)
            db.session.add(user_title)
            db.session.commit()
            add_notification(user, f"Əfsanəvi ünvan qazandın: {title.name}")
            if user.title_id != title.id:
                user.title_id = title.id
                db.session.commit()

def get_earned_titles(user):
    return user.user_titles

# ---------- HTML ŞABLONLARI (əvvəlki kimi, lakin profilə ünvan idarəsi əlavə olundu) ----------
BASE_HTML = """
<!DOCTYPE html>
<html lang="az" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Mi Digital Verse{% endblock %}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Inter:wght@300;400;600;700&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Inter', sans-serif; background: #0f0f1a; color: #e0e0e0; }
        .font-display { font-family: 'Orbitron', sans-serif; }
        .neon-text { text-shadow: 0 0 10px #00f0ff, 0 0 20px #00f0ff; }
        .card-glow:hover { box-shadow: 0 0 20px rgba(0,240,255,0.5); transform: translateY(-5px); transition: all 0.3s; }
        .spoiler { background: #111; color: #111; cursor: pointer; padding: 2px 5px; border-radius: 4px; }
        .spoiler.revealed { background: transparent; color: inherit; }

        /* ===== IŞIQLI REJIM (LIGHT MODE) ===== */
        html.light body {
            background: #f4f6f9;
            color: #111827;
        }
        html.light .bg-gray-900 {
            background-color: #ffffff;
            border-color: #e5e7eb;
            color: #111827;
        }
        html.light .bg-gray-800 {
            background-color: #1f2937; /* Tünd boz - düymələr və kartlar */
            color: #ffffff;
            border: 1px solid #374151;
        }
        html.light .bg-gray-700 {
            background-color: #e5e7eb; /* Açıq boz - inputlar */
            color: #111827;
        }
        html.light .text-gray-300 { color: #374151; }
        html.light .text-gray-400 { color: #4b5563; }
        html.light .text-gray-500 { color: #6b7280; }
        html.light .text-cyan-300 { color: #0e7490; }
        html.light .text-cyan-400 { color: #0891b2; }
        html.light .text-purple-400 { color: #9333ea; }
        html.light .text-purple-500 { color: #7e22ce; }
        html.light .text-yellow-400 { color: #ca8a04; }
        html.light .text-red-400 { color: #dc2626; }
        html.light .text-red-500 { color: #b91c1c; }
        html.light input,
        html.light textarea,
        html.light select {
            background-color: #ffffff;
            color: #111827;
            border: 1px solid #d1d5db;
        }
        html.light nav, html.light footer {
            background-color: #ffffff;
            border-color: #e5e7eb;
        }
        html.light .hero-section {
            background: linear-gradient(135deg, #e0f2fe, #bae6fd, #7dd3fc);
        }
        html.light .hero-section h1 {
            color: #0c4a6e;
            text-shadow: 0 0 5px #7dd3fc;
        }
        html.light .hero-section p {
            color: #1e293b;
        }
        /* Mobil menyu və düymələr üçün */
        html.light #mobileMenu {
            background-color: #ffffff;
            border-bottom: 1px solid #e5e7eb;
        }
        html.light #mobileMenu a,
        html.light #mobileMenu button {
            color: #111827;
        }
        html.light #themeToggle,
        html.light #themeToggleMobile,
        html.light #langToggle,
        html.light #langToggleMobile,
        html.light #mobileMenuBtn {
            background-color: #1f2937;
            color: #ffffff;
        }
    </style>
</head>
<body>
<div class="min-h-screen flex flex-col">
    <nav class="bg-gray-900 bg-opacity-90 backdrop-blur sticky top-0 z-50 border-b border-gray-700">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div class="flex justify-between items-center h-16">
                <div class="flex items-center">
                    <a href="/" class="font-display text-2xl font-bold text-cyan-400 neon-text">Mi Digital Verse</a>
                </div>
                <div class="hidden md:flex space-x-4">
                    <a href="/" class="text-gray-300 hover:text-cyan-400">Ana Səhifə</a>
                    <a href="/news" class="text-gray-300 hover:text-cyan-400">Xəbərlər</a>
                    <div class="relative group">
                        <button class="text-gray-300 hover:text-cyan-400">Kitabxana ▾</button>
                        <div class="absolute left-0 top-full pt-2 w-40 bg-gray-800 rounded-lg shadow-lg hidden group-hover:block">
                            <a href="/category/anime" class="block px-4 py-2 text-sm hover:bg-gray-700">Anime</a>
                            <a href="/category/manga" class="block px-4 py-2 text-sm hover:bg-gray-700">Manga</a>
                            <a href="/category/webtoon" class="block px-4 py-2 text-sm hover:bg-gray-700">Webtoon</a>
                            <a href="/category/manhua" class="block px-4 py-2 text-sm hover:bg-gray-700">Manhua</a>
                            <a href="/category/game" class="block px-4 py-2 text-sm hover:bg-gray-700">Oyun</a>
                            <a href="/manga" class="block px-4 py-2 text-sm hover:bg-gray-700">Bütün Kitabxana</a>
                        </div>
                    </div>
                    <a href="/community" class="text-gray-300 hover:text-cyan-400">İcma</a>
                    <a href="/about" class="text-gray-300 hover:text-cyan-400">Haqqımızda</a>
                    {% if current_user.is_authenticated %}
                    <a href="/profile" class="text-gray-300 hover:text-cyan-400">Profil</a>
                    {% if current_user.is_admin %}
                    <a href="/admin" class="text-yellow-400 hover:text-yellow-300">Admin</a>
                    {% endif %}
                    <a href="/notifications" class="text-gray-300 hover:text-cyan-400 relative">
                        🔔
                        <span id="notif-badge" class="absolute -top-1 -right-1 bg-red-500 text-white rounded-full px-1 text-xs {% if unread_notifications_count == 0 %}hidden{% endif %}">{{ unread_notifications_count }}</span>
                    </a>
                    <a href="/logout" class="text-red-400 hover:text-red-300">Çıxış</a>
                    {% else %}
                    <button onclick="openModal()" class="text-cyan-400 hover:text-cyan-300">Giriş / Qeydiyyat</button>
                    {% endif %}
                </div>
                <div class="flex items-center space-x-3">
                    <!-- Axtarış yalnız masaüstü -->
                    <a href="/news" class="p-2 rounded bg-gray-800 text-white hidden md:inline-block">🔍</a>
                    <!-- Bildiriş zəngi həmişə -->
                    <a href="/notifications" class="p-2 rounded bg-gray-800 text-white relative">
                        🔔
                        <span id="notif-badge" class="absolute -top-1 -right-1 bg-red-500 text-white rounded-full px-1 text-xs {% if unread_notifications_count == 0 %}hidden{% endif %}">{{ unread_notifications_count }}</span>
                    </a>
                    <!-- Dil və tema yalnız masaüstü -->
                    <button id="langToggle" class="p-2 rounded bg-gray-800 text-white hidden md:inline-block">AZ</button>
                    <button id="themeToggle" style="display:none;" class="p-2 rounded-full bg-gray-800 text-yellow-400 hidden md:inline-block">🌙</button>
                    <!-- Mobil menyu düyməsi -->
                    <button id="mobileMenuBtn" class="md:hidden p-2 rounded bg-gray-800 text-white" onclick="document.getElementById('mobileMenu').classList.toggle('hidden')">☰</button>
                </div>
            </div>
        </div>
        <div id="mobileMenu" class="hidden md:hidden bg-gray-900 px-4 pb-4">
            <div class="flex justify-between items-center py-2">
                <button id="langToggleMobile" class="p-2 rounded bg-gray-800 text-white">AZ</button>
                <button id="themeToggleMobile" style="display:none;" class="p-2 rounded-full bg-gray-800 text-yellow-400">🌙</button>
            </div>
            <a href="/" class="block py-2 text-gray-300">Ana Səhifə</a>
            <a href="/news" class="block py-2 text-gray-300">Xəbərlər</a>
            <a href="/category/anime" class="block py-2 text-gray-300">Anime</a>
            <a href="/category/manga" class="block py-2 text-gray-300">Manga</a>
            <a href="/category/webtoon" class="block py-2 text-gray-300">Webtoon</a>
            <a href="/category/manhua" class="block py-2 text-gray-300">Manhua</a>
            <a href="/category/game" class="block py-2 text-gray-300">Oyun</a>
            <a href="/manga" class="block py-2 text-gray-300">Kitabxana</a>
            <a href="/community" class="block py-2 text-gray-300">İcma</a>
            <a href="/about" class="block py-2 text-gray-300">Haqqımızda</a>
            {% if current_user.is_authenticated %}
            <a href="/profile" class="block py-2 text-gray-300">Profil</a>
            <a href="/notifications" class="block py-2 text-gray-300">Bildirişlər</a>
            <a href="/logout" class="block py-2 text-red-400">Çıxış</a>
            {% else %}
            <button onclick="openModal()" class="block py-2 text-cyan-400">Giriş / Qeydiyyat</button>
            {% endif %}
        </div>
    </nav>

    <div id="authModal" class="fixed inset-0 bg-black bg-opacity-70 hidden z-50 flex items-center justify-center p-4">
        <div class="bg-gray-800 rounded-lg p-6 w-full max-w-md relative">
            <button onclick="closeModal()" class="absolute top-3 right-3 text-gray-400 text-2xl">&times;</button>
            <div class="flex justify-center mb-4 space-x-4">
                <button id="loginTabBtn" onclick="showLogin()" class="px-4 py-2 text-cyan-400 border-b-2 border-cyan-400">Giriş</button>
                <button id="registerTabBtn" onclick="showRegister()" class="px-4 py-2 text-gray-400 border-b-2 border-transparent">Qeydiyyat</button>
            </div>
            <form id="loginForm" action="/login" method="POST" class="space-y-3">
                <input type="text" name="username" placeholder="İstifadəçi adı" required class="w-full p-2 rounded bg-gray-700 text-white">
                <input type="password" name="password" placeholder="Şifrə" required class="w-full p-2 rounded bg-gray-700 text-white">
                <button type="submit" class="w-full py-2 bg-cyan-500 hover:bg-cyan-600 text-white rounded">Daxil ol</button>
            </form>
            <form id="registerForm" action="/register" method="POST" class="space-y-3 hidden">
                <input type="text" name="username" placeholder="İstifadəçi adı" required class="w-full p-2 rounded bg-gray-700 text-white">
                <input type="email" name="email" placeholder="Email" class="w-full p-2 rounded bg-gray-700 text-white">
                <input type="password" name="password" placeholder="Şifrə (ən az 8 simvol)" required class="w-full p-2 rounded bg-gray-700 text-white">
                <button type="submit" class="w-full py-2 bg-purple-500 hover:bg-purple-600 text-white rounded">Qeydiyyatdan keç</button>
            </form>
        </div>
    </div>

    <main class="flex-grow">
        <div id="flash-container" class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mt-4">
            {% with messages = get_flashed_messages() %}
                {% if messages %}
                    {% for message in messages %}
                        <div class="bg-cyan-500 text-white px-4 py-2 rounded mb-3 flash-item">{{ message }}</div>
                    {% endfor %}
                {% endif %}
            {% endwith %}
        </div>
<!-- Report Modal -->
<div id="reportModal" class="fixed inset-0 bg-black bg-opacity-70 hidden z-50 flex items-center justify-center p-4">
    <div class="bg-gray-800 rounded-lg p-6 w-full max-w-md relative">
        <button onclick="closeReportModal()" class="absolute top-3 right-3 text-gray-400 text-2xl">&times;</button>
        <h3 class="text-xl font-bold mb-4">Şikayət et</h3>
        <form action="/report/submit" method="POST" class="space-y-3">
            <input type="hidden" name="target_type" id="reportTargetType">
            <input type="hidden" name="target_id" id="reportTargetId">
            <div>
                <label class="text-sm text-gray-400">Səbəb</label>
                <select name="reason" class="w-full p-2 rounded bg-gray-700 text-white" required>
                    <option value="">Səbəb seçin</option>
                    <option value="söyüş">Söyüş</option>
                    <option value="spoiler">Spoiler paylaşır</option>
                    <option value="təhqir">Təhqir edici</option>
                    <option value="spam">Spam</option>
                    <option value="digər">Digər</option>
                </select>
            </div>
            <button type="submit" class="w-full py-2 bg-red-500 hover:bg-red-600 text-white rounded">Göndər</button>
        </form>
    </div>
</div>
        {% block content %}{% endblock %}
    </main>

    <footer class="bg-gray-900 text-gray-400 py-6 border-t border-gray-700">
        <div class="max-w-7xl mx-auto text-center">
            <p>© {{ now.year }} Mi Digital Verse. Bütün hüquqlar qorunur.</p>
        </div>
    </footer>
</div>

<script>        const html = document.documentElement;
    html.classList.add('dark');
    html.classList.remove('light');
    document.getElementById('themeToggle').addEventListener('click', toggleTheme);
    document.getElementById('themeToggleMobile').addEventListener('click', toggleTheme);
    document.getElementById('mobileMenuBtn').addEventListener('click', () => {
        document.getElementById('mobileMenu').classList.toggle('hidden');
    });
    function openModal() { document.getElementById('authModal').classList.remove('hidden'); }
    function closeModal() { document.getElementById('authModal').classList.add('hidden'); }
function openReportModal(type, id) {
    document.getElementById('reportTargetType').value = type;
    document.getElementById('reportTargetId').value = id;
    document.getElementById('reportModal').classList.remove('hidden');
}
function closeReportModal() {
    document.getElementById('reportModal').classList.add('hidden');
}
    // Flash mesajlarını 5 saniyə sonra yoxa çıxar
    setTimeout(function() {
        var flashContainer = document.getElementById('flash-container');
        if (flashContainer) {
            flashContainer.style.transition = 'opacity 0.5s';
            flashContainer.style.opacity = '0';
            setTimeout(function() {
                flashContainer.style.display = 'none';
            }, 500);
        }
    }, 5000);
    function showLogin() {
        document.getElementById('loginForm').classList.remove('hidden');
        document.getElementById('registerForm').classList.add('hidden');
        document.getElementById('loginTabBtn').classList.remove('text-gray-400', 'border-transparent');
        document.getElementById('loginTabBtn').classList.add('text-cyan-400', 'border-cyan-400');
        document.getElementById('registerTabBtn').classList.remove('text-purple-400', 'border-purple-400');
        document.getElementById('registerTabBtn').classList.add('text-gray-400', 'border-transparent');
    }
    function showRegister() {
        document.getElementById('registerForm').classList.remove('hidden');
        document.getElementById('loginForm').classList.add('hidden');
        document.getElementById('registerTabBtn').classList.remove('text-gray-400', 'border-transparent');
        document.getElementById('registerTabBtn').classList.add('text-purple-400', 'border-purple-400');
        document.getElementById('loginTabBtn').classList.remove('text-cyan-400', 'border-cyan-400');
        document.getElementById('loginTabBtn').classList.add('text-gray-400', 'border-transparent');
    }
    // Dil sistemi
    const translations = {
        az: { home: "Ana Səhifə", news: "Xəbərlər", library: "Kitabxana ▾", community: "İcma", about: "Haqqımızda", profile: "Profil", quests: "Görəvlər", achievements: "Nailiyyətlər", admin: "Admin", logout: "Çıxış", login: "Giriş / Qeydiyyat" },
        en: { home: "Home", news: "News", library: "Library ▾", community: "Community", about: "About", profile: "Profile", quests: "Quests", achievements: "Achievements", admin: "Admin", logout: "Logout", login: "Sign In / Join" }
    };
    let currentLang = localStorage.getItem('lang') || 'az';
    applyLanguage(currentLang);
    function applyLanguage(lang) {
        document.querySelectorAll('[data-i18n]').forEach(el => {
            const key = el.getAttribute('data-i18n');
            if (translations[lang] && translations[lang][key]) el.textContent = translations[lang][key];
        });
                const langBtn = document.getElementById('langToggle');
        if (langBtn) langBtn.textContent = lang === 'az' ? 'EN' : 'AZ';
        const langBtnMobile = document.getElementById('langToggleMobile');
        if (langBtnMobile) langBtnMobile.textContent = lang === 'az' ? 'EN' : 'AZ';
        currentLang = lang;
        localStorage.setItem('lang', lang);
    }
    function toggleLanguage() {
        applyLanguage(currentLang === 'az' ? 'en' : 'az');
    }
    const langToggle = document.getElementById('langToggle');
    if (langToggle) langToggle.addEventListener('click', toggleLanguage);
    const langToggleMobile = document.getElementById('langToggleMobile');
    if (langToggleMobile) langToggleMobile.addEventListener('click', toggleLanguage);

    // Flash mesajlarını 5 saniyə sonra yox et
    setTimeout(function() {
        var flashItems = document.querySelectorAll('#flash-container .flash-item, #flash-container div');
        flashItems.forEach(function(item) {
            item.style.transition = 'opacity 0.5s ease';
            item.style.opacity = '0';
            setTimeout(function() {
                item.style.display = 'none';
            }, 500);
        });
    }, 5000);

</script>
</body>
</html>
"""

# Digər bütün şablonlar əvvəlki kimi qalır, lakin profil şablonunu yeniləyirik.
INDEX_HTML = """
{% extends "base.html" %}
{% block title %}Ana Səhifə - Mi Digital Verse{% endblock %}
{% block content %}
<div class="max-w-7xl mx-auto px-4 py-8">
    <div class="hero-section rounded-xl p-8 mb-8 text-center">
        <h1 class="text-4xl md:text-5xl font-bold text-cyan-400 neon-text">Xoş gəldiniz!</h1>
        <p class="text-gray-300 mt-2">Anime, manhwa, manhua və oyun dünyasının ən son xəbərləri</p>
    </div>
    <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div class="col-span-2">
            <h2 class="text-2xl font-semibold mb-4">Son Xəbərlər</h2>
            {% for news in latest_news %}
            <a href="/news/{{ news.id }}" class="block bg-gray-800 rounded-lg p-4 mb-4 card-glow">
                <h3 class="text-xl font-bold text-cyan-300">{{ news.title }}</h3>
                <p class="text-gray-400 text-sm">{{ news.published_at.strftime('%d.%m.%Y') }} | {{ news.category }}</p>
            </a>
            {% else %}
            <p>Hələ xəbər yoxdur.</p>
            {% endfor %}
            <h2 class="text-2xl font-semibold mt-8 mb-4">Ən Çox Oxunanlar</h2>
            {% for news in most_read %}
            <a href="/news/{{ news.id }}" class="block bg-gray-800 rounded-lg p-4 mb-4 card-glow">
                <h3 class="text-xl font-bold text-cyan-300">{{ news.title }}</h3>
                <p class="text-gray-400 text-sm">{{ news.views }} oxunma</p>
            </a>
            {% endfor %}
        </div>
        <div>
            <h2 class="text-2xl font-semibold mb-4">Seçilmiş Manqa/Anime</h2>
            {% for m in featured %}
            <a href="/manga/{{ m.id }}" class="block bg-gray-800 rounded-lg p-3 mb-3 card-glow flex items-center gap-3">
                <img src="{{ m.cover_url }}" alt="{{ m.title }}" class="w-16 h-24 object-cover rounded">
                <div>
                    <h3 class="font-bold">{{ m.title }}</h3>
                    <p class="text-sm text-gray-400">{{ m.type }}</p>
                    <p class="text-yellow-400">Rating: {{ m.rating }}</p>
                </div>
            </a>
            {% endfor %}
        </div>
    </div>
</div>
{% endblock %}
"""

NEWS_LIST_HTML = """
{% extends "base.html" %}
{% block title %}Xəbərlər - Mi Digital Verse{% endblock %}
{% block content %}
<div class="max-w-7xl mx-auto px-4 py-8">
    <h1 class="text-3xl font-bold mb-6">Xəbərlər</h1>
    <form action="/search" method="GET" class="mb-6 flex gap-2">
        <input type="text" name="q" placeholder="Xəbər axtar..." class="flex-1 p-2 rounded bg-gray-800 text-white">
        <button type="submit" class="px-4 py-2 bg-cyan-500 rounded">Axtar</button>
    </form>
    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        {% for news in all_news %}
        <a href="/news/{{ news.id }}" class="block bg-gray-800 rounded-lg p-4 card-glow">
            <h3 class="text-xl font-bold text-cyan-300">{{ news.title }}</h3>
            <p class="text-gray-400">{{ news.category }} | {{ news.published_at.strftime('%d.%m.%Y') }}</p>
            <p class="text-gray-300">{{ news.content[:150] }}...</p>
        </a>
        {% endfor %}
    </div>
</div>
{% endblock %}
"""

NEWS_DETAIL_HTML = """
{% extends "base.html" %}
{% block title %}{{ news.title }} - Mi Digital Verse{% endblock %}
{% block content %}
<div class="max-w-4xl mx-auto px-4 py-8">
    <h1 class="text-3xl font-bold mb-4">{{ news.title }}</h1>
    <p class="text-gray-400">{{ news.category }} | {{ news.published_at.strftime('%d.%m.%Y') }} | Oxunma: {{ news.views }}</p>
    {% if news.image_url %}
    <img src="{{ news.image_url }}" alt="{{ news.title }}" class="w-full max-h-96 object-contain rounded-lg my-4">
    {% endif %}
    <p class="text-lg leading-relaxed" style="white-space: pre-line;">{{ news.content }}</p>
    {% for block in news.blocks %}
        {% if block.block_type == 'text' %}
            {% if block.layout == 'side' %}
                <div class="flex flex-col md:flex-row gap-4 my-4">
                    <div class="flex-1"><p class="text-lg" style="white-space: pre-line;">{{ block.text_content }}</p></div>
                </div>
            {% else %}
                <p class="text-lg my-4" style="white-space: pre-line;">{{ block.text_content }}</p>
            {% endif %}
        {% elif block.block_type == 'image' %}
            {% if block.layout == 'side' %}
                <div class="flex flex-col md:flex-row gap-4 my-4 items-start">
                    <div class="flex-1">
                        {% if block.image_url %}
                            <img src="{{ block.image_url }}" alt="Blok şəkli" class="w-full max-h-96 object-contain rounded-lg">
                        {% endif %}
                    </div>
                </div>
            {% else %}
                <div class="my-4">
                    {% if block.image_url %}
                        <img src="{{ block.image_url }}" alt="Blok şəkli" class="w-full max-h-96 object-contain rounded-lg">
                    {% endif %}
                </div>
            {% endif %}
        {% endif %}
    {% endfor %}
    <div class="mt-6 flex gap-3">
        {% if current_user.is_authenticated %}
        <form action="/like-news/{{ news.id }}" method="POST"><button class="px-4 py-2 bg-red-500 rounded">Bəyən ({{ news.likes }})</button></form>
        {% else %}
        <span class="px-4 py-2 bg-gray-700 rounded">Bəyənmə: {{ news.likes }}</span>
        {% endif %}
        <a href="/create-room?news_id={{ news.id }}" class="px-4 py-2 bg-purple-500 rounded">Bu xəbəri müzakirə et</a>
    </div>
</div>
{% endblock %}
"""

MANGA_LIST_HTML = """
{% extends "base.html" %}
{% block title %}Kitabxana - Mi Digital Verse{% endblock %}
{% block content %}
<div class="max-w-7xl mx-auto px-4 py-8">
    <h1 class="text-3xl font-bold mb-6">Manhwa & Anime Kitabxanası</h1>
    <form action="/manga" method="GET" class="mb-6 flex gap-2">
        <input type="text" name="q" placeholder="Başlıq axtar..." class="flex-1 p-2 rounded bg-gray-800 text-white">
        <select name="type" class="p-2 rounded bg-gray-800 text-white">
            <option value="">Hamısı</option>
            <option value="anime">Anime</option>
            <option value="manga">Manga</option>
            <option value="manhwa">Manhwa</option>
            <option value="manhua">Manhua</option>
            <option value="webtoon">Webtoon</option>
        </select>
        <button type="submit" class="px-4 py-2 bg-cyan-500 rounded">Axtar</button>
    </form>
    <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
        {% for m in mangas %}
        <a href="/manga/{{ m.id }}" class="block bg-gray-800 rounded-lg p-3 card-glow">
            <img src="{{ m.cover_url }}" alt="{{ m.title }}" class="w-full h-64 object-cover rounded">
            <h3 class="font-bold mt-2">{{ m.title }}</h3>
            <p class="text-sm text-gray-400">{{ m.type }} | Rating: {{ m.rating }}</p>
            <p class="text-xs text-gray-500">{{ m.status }} | {{ m.chapters }} bölüm</p>
        </a>
        {% endfor %}
    </div>
</div>
{% endblock %}
"""

MANGA_DETAIL_HTML = """
{% extends "base.html" %}
{% block title %}{{ manga.title }} - Mi Digital Verse{% endblock %}
{% block content %}
<div class="max-w-4xl mx-auto px-4 py-8">
    <h1 class="text-3xl font-bold mb-4">{{ manga.title }}</h1>
    <p class="text-gray-400">{{ manga.type }} | Status: {{ manga.status }} | Bölüm: {{ manga.chapters }} | Oxunma: {{ manga.views }}</p>
    {% if manga.cover_url %}
    <img src="{{ manga.cover_url }}" alt="{{ manga.title }}" class="w-full max-h-96 object-contain rounded-lg my-4">
    {% endif %}
    <p class="text-lg leading-relaxed">{{ manga.description }}</p>
    <p class="text-yellow-400 mt-2">Reytinq: {{ manga.rating }}</p>
    <div class="mt-4 flex gap-3">
        {% if current_user.is_authenticated %}
        <form action="/like-manga/{{ manga.id }}" method="POST"><button class="px-4 py-2 bg-red-500 rounded">Bəyən ({{ manga.likes }})</button></form>
        {% else %}
        <span class="px-4 py-2 bg-gray-700 rounded">Bəyənmə: {{ manga.likes }}</span>
        {% endif %}
        <a href="/community" class="inline-block px-4 py-2 bg-purple-500 rounded">İcma müzakirələri</a>
    </div>
</div>
{% endblock %}
"""

COMMUNITY_HTML = """
{% extends "base.html" %}
{% block title %}İcma - Mi Digital Verse{% endblock %}
{% block content %}
<div class="max-w-7xl mx-auto px-4 py-8">
    <h1 class="text-3xl font-bold mb-6">İcma Müzakirələri</h1>
    {% if current_user.is_authenticated %}
    <form action="/create-room" method="POST" class="mb-6 bg-gray-800 p-4 rounded">
        <input type="text" name="room_name" placeholder="Müzakirə otağı adı" required class="w-full p-2 rounded bg-gray-700 text-white mb-2">
        <select name="news_id" class="w-full p-2 rounded bg-gray-700 text-white mb-2">
            <option value="">Xəbər seç (istəyə bağlı)</option>
            {% for n in all_news %}<option value="{{ n.id }}">{{ n.title }}</option>{% endfor %}
        </select>
        <button type="submit" class="px-4 py-2 bg-cyan-500 rounded">Otaq yarat</button>
    </form>
    {% else %}
    <p class="mb-4">Otaq yaratmaq üçün <a href="#" onclick="openModal()" class="text-cyan-400">giriş edin</a>.</p>
    {% endif %}
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {% for room in rooms %}
        <div class="bg-gray-800 rounded-lg p-4 card-glow flex flex-col">
            <h3 class="font-bold {% if room.name == 'Xəta Otağı' %}text-red-500{% else %}text-cyan-300{% endif %}">{{ room.name }}</h3>
            <p class="text-sm text-gray-400">Yaradıcı: {{ room.creator.username }}</p>
            {% if room.news %}<p class="text-xs text-gray-500">Xəbər: {{ room.news.title }}</p>{% endif %}
            <div class="mt-auto pt-3 flex flex-wrap gap-2 items-center">
                <a href="/room/{{ room.id }}" class="inline-block px-3 py-1 bg-cyan-500 hover:bg-cyan-600 text-white rounded text-sm">Daxil ol</a>
                <button onclick="openReportModal('room', {{ room.id }})" class="px-3 py-1 bg-gray-600 hover:bg-gray-700 text-white rounded text-sm">Şikayət et</button>
                {% if current_user.is_authenticated and current_user.is_admin %}
                    {% if room.name == 'Xəta Otağı' %}
                        <a href="/admin/clear-room-messages/{{ room.id }}" class="px-3 py-1 bg-yellow-500 hover:bg-yellow-600 text-black rounded text-sm" onclick="return confirm('Bütün mesajları silmək istədiyinizə əminsiniz?')">Mesajları təmizlə</a>
                    {% else %}
                        <a href="/admin/delete-room/{{ room.id }}" class="px-3 py-1 bg-red-500 hover:bg-red-600 text-white rounded text-sm" onclick="return confirm('Otağı silmək istədiyinizə əminsiniz?')">Otağı sil</a>
                    {% endif %}
                {% endif %}
            </div>
        </div>
        {% endfor %}
    </div>
</div>
{% endblock %}
"""

ROOM_HTML = """"
{% extends "base.html" %}
{% block title %}{{ room.name }} - Mi Digital Verse{% endblock %}
{% block content %}
<div class="max-w-4xl mx-auto px-4 py-8">
    <h1 class="text-2xl font-bold mb-4">{{ room.name }}</h1>
    {% if current_user.is_authenticated %}
    <form action="/post/{{ room.id }}" method="POST" class="mb-6 bg-gray-800 p-4 rounded">
        <textarea name="content" placeholder="Mesajınız..." required class="w-full p-2 rounded bg-gray-700 text-white" rows="3"></textarea>
        <label class="flex items-center mt-2"><input type="checkbox" name="is_spoiler" value="1" class="mr-2"> Spoiler olaraq işarələ</label>
        <button type="submit" class="mt-2 px-4 py-2 bg-cyan-500 rounded">Göndər</button>
    </form>
    {% else %}
    <p>Yazmaq üçün <a href="#" onclick="openModal()" class="text-cyan-400">giriş edin</a>.</p>
    {% endif %}
    <div class="space-y-4">
        {% for post in posts %}
        <div class="bg-gray-800 rounded p-3">
            <p class="text-sm text-gray-400"><strong>{{ post.user.username }}</strong> | {{ post.created_at.strftime('%d.%m.%Y %H:%M') }}</p>
            {% if current_user.is_authenticated and current_user.is_admin %}
            <a href="/admin/delete-post/{{ post.id }}" class="text-red-400 text-xs">Şərhi sil</a>
            {% endif %}
<button onclick="openReportModal('post', {{ post.id }})" class="text-xs text-gray-500 hover:text-red-400">Şikayət et</button>
            {% if post.is_spoiler %}
            <span class="spoiler" onclick="this.classList.toggle('revealed')">{{ post.content }}</span>
            {% else %}
            <p class="text-gray-300">{{ post.content }}</p>
            {% endif %}
        </div>
        {% endfor %}
    </div>
</div>
{% endblock %}
"""

PROFILE_HTML = """
{% extends "base.html" %}
{% block title %}Profil - Mi Digital Verse{% endblock %}
{% block content %}
<div class="max-w-4xl mx-auto px-4 py-8">
    <h1 class="text-3xl font-bold mb-6">Profil: {{ current_user.username }}</h1>
    <div class="bg-gray-800 rounded-lg p-6">
        {% if current_user.avatar %}
        <img src="{{ url_for('static', filename='uploads/' + current_user.avatar) }}" alt="Avatar" class="w-24 h-24 rounded-full mb-4">
        {% else %}
        <div class="w-24 h-24 rounded-full bg-gray-600 flex items-center justify-center text-4xl mb-4">{{ current_user.username[0].upper() }}</div>
        {% endif %}
        <p>Email: {{ current_user.email }}</p>
        <p>Səviyyə: {{ current_user.get_level() }}</p>
        <p>XP: {{ current_user.points }} / {{ current_user.get_next_level_xp() }}</p>
        <div class="w-full bg-gray-700 rounded-full h-3 mt-2">
            <div class="bg-cyan-500 h-3 rounded-full" style="width: {{ current_user.get_level_progress() }}%"></div>
        </div>
        <p>Günlük giriş seriyası: {{ current_user.streak }} gün</p>
        {% if current_user.title %}
        <p>Aktiv Ünvan: <span style="color: {{ current_user.title.color }};">{{ current_user.title.name }}</span></p>
        {% endif %}
        {% if not claimed_today %}
        <form action="/claim-daily" method="POST"><button class="px-4 py-2 bg-green-500 rounded mt-2">Günlük ödülü al</button></form>
        {% else %}
        <p class="text-green-400 mt-2">Bu gün ödülü almısınız.</p>
        {% endif %}
        <h2 class="text-xl font-bold mt-6 mb-3">Profil şəklini dəyiş</h2>
        <form action="/upload-avatar" method="POST" enctype="multipart/form-data" class="space-y-3">
            <input type="file" name="avatar" accept="image/*" required class="w-full p-2 bg-gray-700 rounded">
            <button type="submit" class="px-4 py-2 bg-purple-500 rounded">Yüklə</button>
        </form>
        <h2 class="text-xl font-bold mt-6 mb-3">Bio və Sosial Keçidlər</h2>
        <form action="/profile/update-bio" method="POST" class="space-y-3">
            <div>
                <label class="text-sm text-gray-400">Bio</label>
                <textarea name="bio" class="w-full p-2 rounded bg-gray-700 text-white" rows="3">{{ current_user.bio or '' }}</textarea>
            </div>
            <div>
                <label class="text-sm text-gray-400">Twitter linki</label>
                <input type="text" name="twitter_link" value="{{ current_user.twitter_link or '' }}" class="w-full p-2 rounded bg-gray-700 text-white">
            </div>
            <div>
                <label class="text-sm text-gray-400">Instagram linki</label>
                <input type="text" name="instagram_link" value="{{ current_user.instagram_link or '' }}" class="w-full p-2 rounded bg-gray-700 text-white">
            </div>
            <div>
                <label class="text-sm text-gray-400">Discord linki</label>
                <input type="text" name="discord_link" value="{{ current_user.discord_link or '' }}" class="w-full p-2 rounded bg-gray-700 text-white">
            </div>
            <button type="submit" class="px-4 py-2 bg-purple-500 rounded">Yadda saxla</button>
        </form>
        <h2 class="text-xl font-bold mt-6 mb-3">Şifrəni dəyiş</h2>
        <form action="/profile/change-password" method="POST" class="space-y-3">
            <input type="password" name="current_password" placeholder="Hazırkı şifrə" required class="w-full p-2 rounded bg-gray-700 text-white">
            <input type="password" name="new_password" placeholder="Yeni şifrə (ən az 8 simvol)" required class="w-full p-2 rounded bg-gray-700 text-white">
            <input type="password" name="confirm_password" placeholder="Yeni şifrəni təkrar yaz" required class="w-full p-2 rounded bg-gray-700 text-white">
            <button type="submit" class="px-4 py-2 bg-cyan-500 rounded">Şifrəni yenilə</button>
        </form>
    </div>

    <!-- Ünvanlar bölməsi -->
    <div class="bg-gray-800 rounded-lg p-6 mt-6">
        <h2 class="text-xl font-bold mb-4">Qazandığın Ünvanlar</h2>
        <div class="grid grid-cols-2 md:grid-cols-3 gap-3">
            {% for user_title in earned_titles %}
            <div class="bg-gray-700 p-3 rounded text-center">
                <span style="color: {{ user_title.title.color }};">{{ user_title.title.name }}</span>
                <p class="text-xs text-gray-400">{{ user_title.title.description }}</p>
                <form action="/profile/set-active-title/{{ user_title.title.id }}" method="POST" class="mt-2">
                    <button type="submit" class="text-xs bg-cyan-500 px-2 py-1 rounded">Aktiv et</button>
                </form>
            </div>
            {% endfor %}
        </div>
    </div>

    <!-- Vitrin bölməsi -->
    <div class="bg-gray-800 rounded-lg p-6 mt-6">
        <h2 class="text-xl font-bold mb-4">Vitrin (3 seçim)</h2>
        <form action="/profile/set-showcase" method="POST" class="space-y-3">
            <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
                {% for i in range(1, 4) %}
                <div>
                    <label class="text-sm">Vitrin {{ i }}</label>
                    <select name="showcase{{ i }}" class="w-full p-2 rounded bg-gray-700 text-white">
                        <option value="">Boş</option>
                        {% for ut in earned_titles %}
                        <option value="{{ ut.title.id }}" {% if (i==1 and current_user.showcase1_id == ut.title.id) or (i==2 and current_user.showcase2_id == ut.title.id) or (i==3 and current_user.showcase3_id == ut.title.id) %}selected{% endif %}>{{ ut.title.name }}</option>
                        {% endfor %}
                    </select>
                </div>
                {% endfor %}
            </div>
            <button type="submit" class="px-4 py-2 bg-purple-500 rounded mt-3">Vitrinini yadda saxla</button>
        </form>
    </div>

    <!-- Görəvlər və Nailiyyətlər -->
    <div class="bg-gray-800 rounded-lg p-6 mt-6">
        <h2 class="text-xl font-bold mb-3">Görəvlər</h2>
        <div class="space-y-2">
            {% for quest in daily_quests %}
            <div class="bg-gray-700 p-3 rounded">
                <div class="flex justify-between">
                    <span>{{ quest.name }}</span>
                    <span class="text-cyan-400">{{ quest.reward_xp }} XP</span>
                </div>
                <p class="text-sm text-gray-400">{{ quest.description }}</p>
                {% set progress = user_quests.get(quest.id) %}
                {% if progress and progress.completed %}
                <span class="text-green-400">Tamamlandı ✔</span>
                {% else %}
                <div class="w-full bg-gray-600 rounded-full h-2 mt-1">
                    <div class="bg-cyan-500 h-2 rounded-full" style="width: {{ (progress.progress / quest.target_value) * 100 if progress else 0 }}%"></div>
                </div>
                <p class="text-xs text-gray-500">{{ progress.progress if progress else 0 }} / {{ quest.target_value }}</p>
                {% endif %}
            </div>
            {% endfor %}
            {% for quest in weekly_quests %}
            <div class="bg-gray-700 p-3 rounded">
                <div class="flex justify-between">
                    <span>{{ quest.name }}</span>
                    <span class="text-cyan-400">{{ quest.reward_xp }} XP</span>
                </div>
                <p class="text-sm text-gray-400">{{ quest.description }}</p>
                {% set progress = user_quests.get(quest.id) %}
                {% if progress and progress.completed %}
                <span class="text-green-400">Tamamlandı ✔</span>
                {% else %}
                <div class="w-full bg-gray-600 rounded-full h-2 mt-1">
                    <div class="bg-cyan-500 h-2 rounded-full" style="width: {{ (progress.progress / quest.target_value) * 100 if progress else 0 }}%"></div>
                </div>
                <p class="text-xs text-gray-500">{{ progress.progress if progress else 0 }} / {{ quest.target_value }}</p>
                {% endif %}
            </div>
            {% endfor %}
        </div>
    </div>

    <div class="bg-gray-800 rounded-lg p-6 mt-6">
        <h2 class="text-xl font-bold mb-3">Nailiyyətlər</h2>
        <div class="space-y-2">
            {% for ach in all_achievements %}
            <div class="bg-gray-700 p-3 rounded flex items-center gap-3 {% if ach.hidden and not earned_achievements[ach.id] %}opacity-50{% endif %}">
                <div class="text-2xl">{{ ach.badge_icon }}</div>
                <div>
                    <span class="font-bold">{{ ach.name }}</span>
                    <p class="text-sm text-gray-400">{{ ach.description }}</p>
                    {% if earned_achievements[ach.id] %}
                    <span class="text-green-400">Qazanılıb ✔</span>
                    {% else %}
                    <span class="text-gray-500">Hələ qazanılmayıb</span>
                    {% endif %}
                </div>
            </div>
            {% endfor %}
        </div>
    </div>
</div>
{% endblock %}
"""
USER_PROFILE_HTML = """
{% extends "base.html" %}
{% block title %}{{ profile_user.username }} - Profil{% endblock %}
{% block content %}
<div class="max-w-4xl mx-auto px-4 py-8">
    <h1 class="text-3xl font-bold mb-6">Profil: {{ profile_user.username }}</h1>
    <div class="bg-gray-800 rounded-lg p-6">
        {% if profile_user.avatar %}
        <img src="{{ url_for('static', filename='uploads/' + profile_user.avatar) }}" alt="Avatar" class="w-24 h-24 rounded-full mb-4">
        {% else %}
        <div class="w-24 h-24 rounded-full bg-gray-600 flex items-center justify-center text-4xl mb-4">{{ profile_user.username[0].upper() }}</div>
        {% endif %}
        <p>Email: {{ profile_user.email }}</p>
        <p>Səviyyə: {{ profile_user.get_level() }}</p>
        <p>XP: {{ profile_user.points }}</p>
        {% if profile_user.title %}
        <p>Ünvan: <span style="color: {{ profile_user.title.color }};">{{ profile_user.title.name }}</span></p>
        {% endif %}
        {% if profile_user.bio %}
        <p class="mt-2">Bio: {{ profile_user.bio }}</p>
        {% endif %}
        {% if profile_user.twitter_link or profile_user.instagram_link or profile_user.discord_link %}
        <p class="mt-2">Sosial: 
            {% if profile_user.twitter_link %}<a href="{{ profile_user.twitter_link }}" target="_blank" class="text-blue-400">Twitter</a>{% endif %}
            {% if profile_user.instagram_link %} | <a href="{{ profile_user.instagram_link }}" target="_blank" class="text-pink-400">Instagram</a>{% endif %}
            {% if profile_user.discord_link %} | <a href="{{ profile_user.discord_link }}" target="_blank" class="text-purple-400">Discord</a>{% endif %}
        </p>
        {% endif %}
        <p class="mt-2">
            {% if profile_user.is_banned %}<span class="text-red-400">Banlı</span>{% else %}<span class="text-green-400">Aktiv</span>{% endif %}
            {% if profile_user.is_muted %}<span class="text-yellow-400"> | Susdurulub</span>{% endif %}
        </p>
    </div>

    {% if current_user.is_admin and profile_user.id != current_user.id %}
    <div class="bg-gray-800 rounded-lg p-6 mt-6">
        <h2 class="text-xl font-bold mb-3">Moderasiya</h2>
        <p class="text-sm text-gray-400 mb-2">Ban müddətləri:</p>
        <div class="flex flex-wrap gap-2">
            <a href="/admin/ban-user/{{ profile_user.id }}?duration=1" class="px-3 py-1 bg-red-500 text-white rounded">1 gün</a>
            <a href="/admin/ban-user/{{ profile_user.id }}?duration=7" class="px-3 py-1 bg-red-500 text-white rounded">7 gün</a>
            <a href="/admin/ban-user/{{ profile_user.id }}?duration=30" class="px-3 py-1 bg-red-500 text-white rounded">30 gün</a>
            <a href="/admin/ban-user/{{ profile_user.id }}?duration=90" class="px-3 py-1 bg-red-500 text-white rounded">3 ay</a>
            <a href="/admin/ban-user/{{ profile_user.id }}?duration=180" class="px-3 py-1 bg-red-500 text-white rounded">6 ay</a>
            <a href="/admin/ban-user/{{ profile_user.id }}?duration=365" class="px-3 py-1 bg-red-500 text-white rounded">12 ay</a>
            <a href="/admin/ban-user/{{ profile_user.id }}?duration=forever" class="px-3 py-1 bg-red-700 text-white rounded">Ömürlük</a>
            {% if profile_user.is_banned %}<a href="/admin/unban-user/{{ profile_user.id }}" class="px-3 py-1 bg-green-500 text-white rounded">Banı aç</a>{% endif %}
        </div>
        <p class="text-sm text-gray-400 mt-4 mb-2">Susdurma müddətləri:</p>
        <div class="flex flex-wrap gap-2">
            <a href="/admin/mute-user/{{ profile_user.id }}?duration=1" class="px-3 py-1 bg-yellow-500 text-white rounded">1 gün</a>
            <a href="/admin/mute-user/{{ profile_user.id }}?duration=7" class="px-3 py-1 bg-yellow-500 text-white rounded">7 gün</a>
            <a href="/admin/mute-user/{{ profile_user.id }}?duration=30" class="px-3 py-1 bg-yellow-500 text-white rounded">30 gün</a>
            {% if profile_user.is_muted %}<a href="/admin/unmute-user/{{ profile_user.id }}" class="px-3 py-1 bg-green-500 text-white rounded">Susturmanı aç</a>{% endif %}
        </div>
    </div>
    {% endif %}
</div>
{% endblock %}
"""

ADMIN_HTML = """
{% extends "base.html" %}
{% block title %}Admin Panel - Mi Digital Verse{% endblock %}
{% block content %}
<div class="max-w-7xl mx-auto px-4 py-8">
    <h1 class="text-3xl font-bold mb-6">Admin Panel</h1>
    <div class="mb-6">
    <div class="mb-6 bg-gray-800 p-4 rounded">
        <h2 class="text-xl font-bold mb-3">Siyahı Məqaləsi Yarat</h2>
        <form action="/admin/generate-listicle" method="POST" class="space-y-3">
            <input type="text" name="topic" placeholder="Məsələn: best 10 isekai anime 2026" required class="w-full p-2 rounded bg-gray-700 text-white">
            <button type="submit" class="px-4 py-2 bg-purple-500 hover:bg-purple-600 text-white rounded">Siyahı yarat</button>
        </form>
    </div>
        <a href="/admin/fetch-news" class="px-4 py-2 bg-green-500 hover:bg-green-600 text-white rounded">Son xəbərləri avtomatik çək</a>
    </div>
    <div class="grid grid-cols-1 md:grid-cols-2 gap-8">
        <div class="bg-gray-800 p-4 rounded">
            <h2 class="text-xl font-bold mb-3">Yeni Xəbər Əlavə Et</h2>
            <form action="/admin/add-news" method="POST" enctype="multipart/form-data" class="space-y-3">
                <input type="text" name="title" placeholder="Başlıq" required class="w-full p-2 rounded bg-gray-700 text-white">
                <textarea name="content" placeholder="Məzmun" required class="w-full p-2 rounded bg-gray-700 text-white" rows="5"></textarea>
                <input type="text" name="category" placeholder="Kateqoriya (Anime, Manga, Webtoon, Oyun, Ümumi)" value="Anime" class="w-full p-2 rounded bg-gray-700 text-white">
                <input type="text" name="image_url" placeholder="Şəkil URL" class="w-full p-2 rounded bg-gray-700 text-white">
                <div id="blocksContainer"></div>
                <button type="button" onclick="addTextBlock()" class="px-4 py-2 bg-cyan-500 rounded mt-2">+ Mətn Bloku</button>
                <button type="button" onclick="addImageBlock()" class="px-4 py-2 bg-purple-500 rounded mt-2 ml-2">+ Şəkil Bloku</button>		
                <input type="file" name="image_file" accept="image/*" class="w-full p-2 bg-gray-700 rounded text-white">
                <button type="submit" class="px-4 py-2 bg-cyan-500 rounded">Əlavə et</button>
            </form>
        </div>
        <div class="bg-gray-800 p-4 rounded">
            <h2 class="text-xl font-bold mb-3">Yeni Manqa/Anime Əlavə Et</h2>
            <form action="/admin/add-manga" method="POST" enctype="multipart/form-data" class="space-y-3">
                <input type="text" name="title" placeholder="Başlıq" required class="w-full p-2 rounded bg-gray-700 text-white">
                <textarea name="description" placeholder="Açıqlama" required class="w-full p-2 rounded bg-gray-700 text-white" rows="3"></textarea>
                <select name="type" class="w-full p-2 rounded bg-gray-700 text-white">
                    <option value="anime">Anime</option>
                    <option value="manga">Manga</option>
                    <option value="manhwa">Manhwa</option>
                    <option value="manhua">Manhua</option>
                    <option value="webtoon">Webtoon</option>
                </select>
                <input type="text" name="cover_url" placeholder="Üz şəkli URL" class="w-full p-2 rounded bg-gray-700 text-white">
                <input type="file" name="cover_file" accept="image/*" class="w-full p-2 bg-gray-700 rounded text-white">
                <input type="number" step="0.1" name="rating" placeholder="Reytinq (məs. 8.5)" class="w-full p-2 rounded bg-gray-700 text-white">
                <input type="text" name="status" placeholder="Status" value="Davam edir" class="w-full p-2 rounded bg-gray-700 text-white">
                <input type="number" name="chapters" placeholder="Bölüm sayı" value="100" class="w-full p-2 rounded bg-gray-700 text-white">
                <button type="submit" class="px-4 py-2 bg-purple-500 rounded">Əlavə et</button>
            </form>
        </div>
    </div>
    <h2 class="text-2xl font-bold mt-8 mb-3">Qaralamalar</h2>
    <div class="space-y-2">
        {% for draft in draft_news %}
        <div class="bg-gray-800 p-3 rounded flex justify-between items-center">
            <span>{{ draft.title }}</span>
            <div>
                <a href="/admin/publish-news/{{ draft.id }}" class="text-green-400 mr-3">Yayımla</a>
                <a href="/admin/edit-news/{{ draft.id }}" class="text-cyan-400 mr-3">Redaktə et</a>
                <a href="/admin/delete-news/{{ draft.id }}" class="text-red-400">Sil</a>
            </div>
        </div>
        {% endfor %}
    </div>

    <h2 class="text-2xl font-bold mt-8 mb-3">Mövcud Xəbərlər</h2>
    <div class="space-y-2">
        {% for news in all_news %}
        <div class="bg-gray-800 p-3 rounded flex justify-between items-center">
            <span>{{ news.title }}</span>
            <div>
                <a href="/admin/edit-news/{{ news.id }}" class="text-cyan-400 mr-3">Redaktə et</a>
                <a href="/admin/delete-news/{{ news.id }}" class="text-red-400">Sil</a>
            </div>
        </div>
        {% endfor %}
    </div>
    <h2 class="text-2xl font-bold mt-8 mb-3">Mövcud Manqa/Anime</h2>

    <h2 class="text-2xl font-bold mt-8 mb-3">Şikayətlər</h2>
    <div class="space-y-2">
        {% for item in report_details %}
        <div class="bg-gray-800 p-3 rounded">
            <div class="flex justify-between items-start">
                <div>
                    <p><strong>{{ item.report.reporter.username }}</strong> tərəfindən şikayət</p>
                    <p class="text-sm text-gray-400">Növ: {{ item.report.target_type }} #{{ item.report.target_id }}</p>
                    <p class="text-sm text-gray-400">Səbəb: {{ item.report.reason }}</p>
                    <p class="text-xs text-gray-500 mt-2">Məzmun: {{ item.snippet }}</p>
                    <a href="{{ item.link }}" class="text-blue-400 text-xs" target="_blank">Məzmuna bax</a>
                </div>
                <div class="flex gap-2">
                    <a href="/admin/handle-report/{{ item.report.id }}" class="text-green-400">Həll et</a>
                    <a href="/admin/delete-report/{{ item.report.id }}" class="text-red-400">Sil</a>
                    {% if item.report.target_type == 'post' %}
                        <a href="/admin/delete-post/{{ item.report.target_id }}" class="text-red-500">Şərhi sil</a>
                    {% elif item.report.target_type == 'room' %}
                        <a href="/admin/delete-room/{{ item.report.target_id }}" class="text-red-500">Otağı sil</a>
                    {% endif %}
                </div>
            </div>
        </div>
        {% endfor %}
    </div>
    </div>
    <div class="space-y-2">
        {% for m in all_manga %}
        <div class="bg-gray-800 p-3 rounded flex justify-between items-center">
            <span>{{ m.title }} ({{ m.type }})</span>
            <div>
                <a href="/admin/edit-manga/{{ m.id }}" class="text-cyan-400 mr-3">Redaktə et</a>
                <a href="/admin/delete-manga/{{ m.id }}" class="text-red-400">Sil</a>
            </div>
        </div>
        {% endfor %}
    </div>
</div>
<script>
    function addTextBlock() {
        const container = document.getElementById('blocksContainer');
        const div = document.createElement('div');
        div.className = 'bg-gray-700 p-3 rounded mt-3';
        div.innerHTML = `
            <div class="flex justify-between items-center mb-2">
                <span class="font-bold">Mətn Bloku</span>
                <button type="button" onclick="this.parentElement.parentElement.remove()" class="text-red-400">Sil</button>
            </div>
            <input type="hidden" name="block_type" value="text">
            <textarea name="block_text" class="w-full p-2 rounded bg-gray-800 text-white" rows="4" placeholder="Mətn daxil edin"></textarea>
            <select name="block_layout" class="w-full p-2 rounded bg-gray-800 text-white mt-2">
                <option value="stack">Alt-alta</option>
                <option value="side">Yan-yana</option>
            </select>
        `;
        container.appendChild(div);
    }

    function addImageBlock() {
        const container = document.getElementById('blocksContainer');
        const div = document.createElement('div');
        div.className = 'bg-gray-700 p-3 rounded mt-3';
        div.innerHTML = `
            <div class="flex justify-between items-center mb-2">
                <span class="font-bold">Şəkil Bloku</span>
                <button type="button" onclick="this.parentElement.parentElement.remove()" class="text-red-400">Sil</button>
            </div>
            <input type="hidden" name="block_type" value="image">
            <input type="text" name="block_image_url" placeholder="Şəkil URL" class="w-full p-2 rounded bg-gray-800 text-white">
            <input type="file" name="block_image_file" accept="image/*" class="w-full p-2 bg-gray-800 rounded text-white mt-2">
            <select name="block_layout" class="w-full p-2 rounded bg-gray-800 text-white mt-2">
                <option value="stack">Alt-alta</option>
                <option value="side">Yan-yana</option>
            </select>
        `;
        container.appendChild(div);
    }
</script>
{% endblock %}
"""

EDIT_NEWS_HTML = """
{% extends "base.html" %}
{% block title %}Xəbəri Redaktə Et - Mi Digital Verse{% endblock %}
{% block content %}
<div class="max-w-4xl mx-auto px-4 py-8">
    <h1 class="text-3xl font-bold mb-6">Xəbəri Redaktə Et</h1>
    <form method="POST" enctype="multipart/form-data" class="bg-gray-800 p-4 rounded space-y-3">
        <input type="text" name="title" value="{{ news.title }}" required class="w-full p-2 rounded bg-gray-700 text-white">
        <textarea name="content" required class="w-full p-2 rounded bg-gray-700 text-white" rows="8">{{ news.content }}</textarea>
        <input type="text" name="category" value="{{ news.category }}" class="w-full p-2 rounded bg-gray-700 text-white">
        <input type="text" name="image_url" value="{{ news.image_url }}" class="w-full p-2 rounded bg-gray-700 text-white">
        <input type="file" name="image_file" accept="image/*" class="w-full p-2 bg-gray-700 rounded text-white">

        <!-- Dinamik Bloklar -->
        <h2 class="text-xl font-bold mt-6 mb-3">Əlavə Bloklar (mətn/şəkil)</h2>
        <div id="blocksContainer"></div>
        <button type="button" onclick="addTextBlock()" class="px-4 py-2 bg-cyan-500 rounded mt-2">+ Mətn Bloku</button>
        <button type="button" onclick="addImageBlock()" class="px-4 py-2 bg-purple-500 rounded mt-2 ml-2">+ Şəkil Bloku</button>

        <button type="submit" class="px-4 py-2 bg-green-500 rounded mt-4">Yadda saxla</button>
    </form>
</div>

<script>
    let blockIndex = 0;

    function addTextBlock() {
        const container = document.getElementById('blocksContainer');
        const div = document.createElement('div');
        div.className = 'bg-gray-700 p-3 rounded mt-3';
        div.innerHTML = `
            <div class="flex justify-between items-center mb-2">
                <span class="font-bold">Mətn Bloku</span>
                <button type="button" onclick="this.parentElement.parentElement.remove()" class="text-red-400">Sil</button>
            </div>
            <input type="hidden" name="block_type" value="text">
            <textarea name="block_text" class="w-full p-2 rounded bg-gray-800 text-white" rows="4" placeholder="Mətn daxil edin"></textarea>
            <select name="block_layout" class="w-full p-2 rounded bg-gray-800 text-white mt-2">
                <option value="stack">Alt-alta</option>
                <option value="side">Yan-yana</option>
            </select>
        `;
        container.appendChild(div);
        blockIndex++;
    }

    function addImageBlock() {
        const container = document.getElementById('blocksContainer');
        const div = document.createElement('div');
        div.className = 'bg-gray-700 p-3 rounded mt-3';
        div.innerHTML = `
            <div class="flex justify-between items-center mb-2">
                <span class="font-bold">Şəkil Bloku</span>
                <button type="button" onclick="this.parentElement.parentElement.remove()" class="text-red-400">Sil</button>
            </div>
            <input type="hidden" name="block_type" value="image">
            <input type="text" name="block_image_url" placeholder="Şəkil URL" class="w-full p-2 rounded bg-gray-800 text-white">
            <input type="file" name="block_image_file" accept="image/*" class="w-full p-2 bg-gray-800 rounded text-white mt-2">
            <select name="block_layout" class="w-full p-2 rounded bg-gray-800 text-white mt-2">
                <option value="stack">Alt-alta</option>
                <option value="side">Yan-yana</option>
            </select>
        `;
        container.appendChild(div);
        blockIndex++;
    }

    // Mövcud blokları yüklə (əgər varsa)
    window.onload = function() {
        {% for block in news.blocks %}
            {% if block.block_type == 'text' %}
                const textDiv{{ block.id }} = document.createElement('div');
                textDiv{{ block.id }}.className = 'bg-gray-700 p-3 rounded mt-3';
                textDiv{{ block.id }}.innerHTML = `
                    <div class="flex justify-between items-center mb-2">
                        <span class="font-bold">Mətn Bloku</span>
                        <button type="button" onclick="this.parentElement.parentElement.remove()" class="text-red-400">Sil</button>
                    </div>
                    <input type="hidden" name="block_type" value="text">
                    <textarea name="block_text" class="w-full p-2 rounded bg-gray-800 text-white" rows="4" placeholder="Mətn daxil edin">{{ block.text_content }}</textarea>
                    <select name="block_layout" class="w-full p-2 rounded bg-gray-800 text-white mt-2">
                        <option value="stack" {% if block.layout == 'stack' %}selected{% endif %}>Alt-alta</option>
                        <option value="side" {% if block.layout == 'side' %}selected{% endif %}>Yan-yana</option>
                    </select>
                `;
                document.getElementById('blocksContainer').appendChild(textDiv{{ block.id }});
            {% else %}
                const imgDiv{{ block.id }} = document.createElement('div');
                imgDiv{{ block.id }}.className = 'bg-gray-700 p-3 rounded mt-3';
                imgDiv{{ block.id }}.innerHTML = `
                    <div class="flex justify-between items-center mb-2">
                        <span class="font-bold">Şəkil Bloku</span>
                        <button type="button" onclick="this.parentElement.parentElement.remove()" class="text-red-400">Sil</button>
                    </div>
                    <input type="hidden" name="block_type" value="image">
                    <input type="text" name="block_image_url" placeholder="Şəkil URL" value="{{ block.image_url }}" class="w-full p-2 rounded bg-gray-800 text-white">
                    <input type="file" name="block_image_file" accept="image/*" class="w-full p-2 bg-gray-800 rounded text-white mt-2">
                    <select name="block_layout" class="w-full p-2 rounded bg-gray-800 text-white mt-2">
                        <option value="stack" {% if block.layout == 'stack' %}selected{% endif %}>Alt-alta</option>
                        <option value="side" {% if block.layout == 'side' %}selected{% endif %}>Yan-yana</option>
                    </select>
                `;
                document.getElementById('blocksContainer').appendChild(imgDiv{{ block.id }});
            {% endif %}
        {% endfor %}
    };
</script>
{% endblock %}
"""

EDIT_MANGA_HTML = """
{% extends "base.html" %}
{% block title %}Manqanı Redaktə Et - Mi Digital Verse{% endblock %}
{% block content %}
<div class="max-w-4xl mx-auto px-4 py-8">
    <h1 class="text-3xl font-bold mb-6">Manqanı Redaktə Et</h1>
    <form method="POST" enctype="multipart/form-data" class="bg-gray-800 p-4 rounded space-y-3">
        <input type="text" name="title" value="{{ manga.title }}" required class="w-full p-2 rounded bg-gray-700 text-white">
        <textarea name="description" required class="w-full p-2 rounded bg-gray-700 text-white" rows="5">{{ manga.description }}</textarea>
        <select name="type" class="w-full p-2 rounded bg-gray-700 text-white">
            <option value="anime" {% if manga.type == 'anime' %}selected{% endif %}>Anime</option>
            <option value="manga" {% if manga.type == 'manga' %}selected{% endif %}>Manga</option>
            <option value="manhwa" {% if manga.type == 'manhwa' %}selected{% endif %}>Manhwa</option>
            <option value="manhua" {% if manga.type == 'manhua' %}selected{% endif %}>Manhua</option>
            <option value="webtoon" {% if manga.type == 'webtoon' %}selected{% endif %}>Webtoon</option>
        </select>
        <input type="text" name="cover_url" value="{{ manga.cover_url }}" class="w-full p-2 rounded bg-gray-700 text-white">
        <input type="file" name="cover_file" accept="image/*" class="w-full p-2 bg-gray-700 rounded text-white">
        <input type="number" step="0.1" name="rating" value="{{ manga.rating }}" class="w-full p-2 rounded bg-gray-700 text-white">
        <input type="text" name="status" value="{{ manga.status }}" class="w-full p-2 rounded bg-gray-700 text-white">
        <input type="number" name="chapters" value="{{ manga.chapters }}" class="w-full p-2 rounded bg-gray-700 text-white">
        <button type="submit" class="px-4 py-2 bg-purple-500 rounded">Yadda saxla</button>
    </form>
</div>
{% endblock %}
"""

ABOUT_HTML = """
{% extends "base.html" %}
{% block title %}Haqqımızda - Mi Digital Verse{% endblock %}
{% block content %}
<div class="max-w-4xl mx-auto px-4 py-8">
    <h1 class="text-3xl font-bold mb-6">Haqqımızda</h1>
<p class="text-lg leading-relaxed mb-4">
    Mi Digital Verse, anime, manhwa, manhua və manga həvəskarları üçün yaradılmış müasir rəqəmsal məkandır.
    Məqsədimiz pərəstişkarlara ən son xəbərləri, keyfiyyətli analizləri və interaktiv icma təcrübəsini bir araya gətirməkdir.
</p>
<p class="text-lg leading-relaxed mb-4">
    Biz inanırıq ki, hər bir pərəstişkarın səsi burada eşidilməlidir. Ona görə də saytımızda müzakirə otaqları, nailiyyətlər və ünvan sistemi qurmuşuq.
    Gələcəkdə daha çox funksiya və məzmun əlavə edərək böyüməyə davam edəcəyik.
</p>
<p class="text-lg leading-relaxed">
    Mi Digital Verse ailəsinə qoşulun və rəqəmsal dünyada öz yerinizi alın!
</p>
</div>
{% endblock %}
"""

SEARCH_HTML = """
{% extends "base.html" %}
{% block title %}Axtarış - Mi Digital Verse{% endblock %}
{% block content %}
<div class="max-w-7xl mx-auto px-4 py-8">
    <h1 class="text-2xl mb-4">Axtarış: "{{ q }}"</h1>
    <h2 class="text-xl mb-3">Xəbərlər</h2>
    {% for n in news_results %}
    <div class="bg-gray-800 p-3 rounded mb-2"><a href="/news/{{ n.id }}" class="text-cyan-300">{{ n.title }}</a></div>
    {% else %}<p>Tapılmadı.</p>{% endfor %}
    <h2 class="text-xl mb-3 mt-6">Manqa/Anime</h2>
    {% for m in manga_results %}
    <div class="bg-gray-800 p-3 rounded mb-2"><a href="/manga/{{ m.id }}" class="text-cyan-300">{{ m.title }} ({{ m.type }})</a></div>
    {% else %}<p>Tapılmadı.</p>{% endfor %}
</div>
{% endblock %}
"""

NOTIFICATIONS_HTML = """
{% extends "base.html" %}
{% block title %}Bildirişlər - Mi Digital Verse{% endblock %}
{% block content %}
<div class="max-w-4xl mx-auto px-4 py-8">
    <h1 class="text-3xl font-bold mb-6">Bildirişlər</h1>
    <div class="space-y-2">
        {% for n in notifications %}
        <div class="bg-gray-800 p-3 rounded flex justify-between items-center {% if not n.is_read %}border-l-4 border-cyan-400{% endif %}">
            <p class="text-gray-300">{{ n.message }}</p>
            <div class="text-sm text-gray-400">
                {{ n.created_at.strftime('%d.%m.%Y %H:%M') }}
                {% if not n.is_read %}
                <a href="/notifications/mark-read/{{ n.id }}" class="ml-2 text-cyan-400">Oxunmuş işarələ</a>
                {% endif %}
            </div>
        </div>
        {% else %}
        <p>Bildiriş yoxdur.</p>
        {% endfor %}
    </div>
    <a href="/notifications/mark-all-read" class="mt-4 inline-block px-4 py-2 bg-cyan-500 rounded">Hamısını oxunmuş et</a>
</div>
{% endblock %}
"""

QUESTS_HTML = """
{% extends "base.html" %}
{% block title %}Görəvlər - Mi Digital Verse{% endblock %}
{% block content %}
<div class="max-w-4xl mx-auto px-4 py-8">
    <h1 class="text-3xl font-bold mb-6">Görəvlər</h1>
    <h2 class="text-2xl font-semibold mb-3">Gündəlik</h2>
    <div class="space-y-3">
        {% for quest in daily_quests %}
        <div class="bg-gray-800 p-4 rounded">
            <div class="flex justify-between">
                <span class="font-bold">{{ quest.name }}</span>
                <span class="text-cyan-400">{{ quest.reward_xp }} XP</span>
            </div>
            <p class="text-sm text-gray-400">{{ quest.description }}</p>
            {% set progress = user_quests.get(quest.id) %}
            {% if progress %}
                {% if progress.completed %}
                <p class="text-green-400">Tamamlandı ✔</p>
                {% else %}
                <div class="w-full bg-gray-700 rounded-full h-2 mt-2">
                    <div class="bg-cyan-500 h-2 rounded-full" style="width: {{ (progress.progress / quest.target_value) * 100 }}%"></div>
                </div>
                <p class="text-xs text-gray-500">{{ progress.progress }} / {{ quest.target_value }}</p>
                {% endif %}
            {% else %}
                <p class="text-xs text-gray-500">0 / {{ quest.target_value }}</p>
            {% endif %}
        </div>
        {% endfor %}
    </div>

    <h2 class="text-2xl font-semibold mt-8 mb-3">Həftəlik</h2>
    <div class="space-y-3">
        {% for quest in weekly_quests %}
        <div class="bg-gray-800 p-4 rounded">
            <div class="flex justify-between">
                <span class="font-bold">{{ quest.name }}</span>
                <span class="text-cyan-400">{{ quest.reward_xp }} XP</span>
            </div>
            <p class="text-sm text-gray-400">{{ quest.description }}</p>
            {% set progress = user_quests.get(quest.id) %}
            {% if progress %}
                {% if progress.completed %}
                <p class="text-green-400">Tamamlandı ✔</p>
                {% else %}
                <div class="w-full bg-gray-700 rounded-full h-2 mt-2">
                    <div class="bg-cyan-500 h-2 rounded-full" style="width: {{ (progress.progress / quest.target_value) * 100 }}%"></div>
                </div>
                <p class="text-xs text-gray-500">{{ progress.progress }} / {{ quest.target_value }}</p>
                {% endif %}
            {% else %}
                <p class="text-xs text-gray-500">0 / {{ quest.target_value }}</p>
            {% endif %}
        </div>
        {% endfor %}
    </div>
</div>
{% endblock %}
"""

ACHIEVEMENTS_HTML = """
{% extends "base.html" %}
{% block title %}Nailiyyətlər - Mi Digital Verse{% endblock %}
{% block content %}
<div class="max-w-4xl mx-auto px-4 py-8">
    <h1 class="text-3xl font-bold mb-6">Nailiyyətlər</h1>
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        {% for ach in all_achievements %}
        <div class="bg-gray-800 p-4 rounded flex items-center gap-3 {% if ach.hidden and not earned_achievements[ach.id] %}opacity-50{% endif %}">
            <div class="text-3xl">{{ ach.badge_icon }}</div>
            <div>
                <p class="font-bold">{{ ach.name }}</p>
                <p class="text-sm text-gray-400">{{ ach.description }}</p>
                {% if earned_achievements[ach.id] %}
                <p class="text-green-400">Qazanılıb ✔</p>
                {% else %}
                <p class="text-gray-500">Hələ qazanılmayıb</p>
                {% endif %}
            </div>
        </div>
        {% endfor %}
    </div>
</div>
{% endblock %}
"""

templates = {
    'base.html': BASE_HTML,
    'index.html': INDEX_HTML,
    'news_list.html': NEWS_LIST_HTML,
    'news_detail.html': NEWS_DETAIL_HTML,
    'manga_list.html': MANGA_LIST_HTML,
    'manga_detail.html': MANGA_DETAIL_HTML,
    'community.html': COMMUNITY_HTML,
    'room.html': ROOM_HTML,
    'profile.html': PROFILE_HTML,
    'user_profile.html': USER_PROFILE_HTML,
    'admin.html': ADMIN_HTML,
    'edit_news.html': EDIT_NEWS_HTML,
    'edit_manga.html': EDIT_MANGA_HTML,
    'search.html': SEARCH_HTML,
    'notifications.html': NOTIFICATIONS_HTML,
    'quests.html': QUESTS_HTML,
    'achievements.html': ACHIEVEMENTS_HTML,
    'about.html': ABOUT_HTML,
}

app.jinja_loader = DictLoader(templates)

@app.context_processor
def inject_now():
    return {'now': datetime.utcnow()}

@app.context_processor
def inject_unread_notifications():
    if current_user.is_authenticated:
        unread = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
        return {'unread_notifications_count': unread}
    return {'unread_notifications_count': 0}

# ---------- ROUTELAR ----------
@app.route('/')
def index():
    latest_news = News.query.filter_by(status='published').order_by(News.published_at.desc()).limit(5).all()
    most_read = News.query.filter_by(status='published').order_by(News.views.desc()).limit(5).all()
    featured = Manga.query.order_by(Manga.rating.desc()).limit(4).all()
    return render_template('index.html', latest_news=latest_news, most_read=most_read, featured=featured)

@app.route('/news')
def news_list():
    all_news = News.query.filter_by(status='published').order_by(News.published_at.desc()).all()
    return render_template('news_list.html', all_news=all_news)

@app.route('/news/<int:news_id>')
def news_detail(news_id):
    news = News.query.get_or_404(news_id)
    if can_increment_view(news.id):
        news.views += 1
        db.session.commit()
        if current_user.is_authenticated:
            current_user.news_read_count += 1
            add_xp(current_user, 2)
            update_quest_progress(current_user, 'news_read', 1)
            check_achievements(current_user)
    return render_template('news_detail.html', news=news)

@app.route('/category/<string:cat>')
def category(cat):
    all_news = News.query.filter(News.status == 'published', News.category.ilike(f'%{cat}%')).order_by(News.published_at.desc()).all()
    return render_template('news_list.html', all_news=all_news)

@app.route('/manga')
def manga_list():
    type_filter = request.args.get('type', '')
    q = request.args.get('q', '')
    if q:
        mangas = Manga.query.filter(Manga.title.contains(q) | Manga.description.contains(q)).all()
    elif type_filter:
        mangas = Manga.query.filter_by(type=type_filter).all()
    else:
        mangas = Manga.query.all()
    return render_template('manga_list.html', mangas=mangas)

@app.route('/manga/<int:manga_id>')
def manga_detail(manga_id):
    manga = Manga.query.get_or_404(manga_id)
    if can_increment_view(manga.id):
        manga.views += 1
        db.session.commit()
    return render_template('manga_detail.html', manga=manga)

@app.route('/like-manga/<int:manga_id>', methods=['POST'])
@login_required
def like_manga(manga_id):
    manga = Manga.query.get_or_404(manga_id)
    manga.likes += 1
    db.session.commit()
    current_user.likes_count += 1
    add_xp(current_user, 1)
    update_quest_progress(current_user, 'like', 1)
    check_achievements(current_user)
    add_notification(current_user, f"Siz {manga.title} əsərini bəyəndiniz.")
    return redirect(url_for('manga_detail', manga_id=manga.id))

@app.route('/search')
def search():
    q = request.args.get('q', '').strip()
    type_filter = request.args.get('type', '')
    news_results = []
    manga_results = []
    if q:
        news_results = News.query.filter(News.status == 'published', News.title.contains(q) | News.content.contains(q)).all()
        manga_results = Manga.query.filter(Manga.title.contains(q) | Manga.description.contains(q)).all()
        if type_filter:
            manga_results = [m for m in manga_results if m.type == type_filter]
    return render_template('search.html', q=q, news_results=news_results, manga_results=manga_results)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/community')
def community():
    rooms = Room.query.order_by(Room.created_at.desc()).all()
    all_news = News.query.all()
    return render_template('community.html', rooms=rooms, all_news=all_news)

@app.route('/create-room', methods=['GET', 'POST'])
@login_required
def create_room():
    if request.method == 'GET':
        all_news = News.query.all()
        selected_news_id = request.args.get('news_id')
        return render_template_string('''
        {% extends "base.html" %}
        {% block content %}
        <div class="max-w-4xl mx-auto px-4 py-8">
            <h1 class="text-3xl font-bold mb-6">Yeni Müzakirə Otağı</h1>
            <form method="POST" class="bg-gray-800 p-4 rounded space-y-3">
                <input type="text" name="room_name" placeholder="Otaq adı" required class="w-full p-2 rounded bg-gray-700 text-white">
                <select name="news_id" class="w-full p-2 rounded bg-gray-700 text-white">
                    <option value="">Xəbər seç (istəyə bağlı)</option>
                    {% for n in all_news %}
                    <option value="{{ n.id }}" {% if n.id == selected_news_id %}selected{% endif %}>{{ n.title }}</option>
                    {% endfor %}
                </select>
                <button type="submit" class="px-4 py-2 bg-cyan-500 rounded">Otağı yarat</button>
            </form>
        </div>
        {% endblock %}
        ''', all_news=all_news, selected_news_id=int(selected_news_id) if selected_news_id else None)
    else:
        name = request.form.get('room_name', '').strip()
        news_id = request.form.get('news_id', '')
        if not name:
            flash('Otaq adı boş ola bilməz')
            return redirect(url_for('community'))
        room = Room(name=name, news_id=int(news_id) if news_id else None, creator_id=current_user.id)
        db.session.add(room)
        db.session.commit()
        update_quest_progress(current_user, 'room_create', 1)
        check_achievements(current_user)
        # Bildiriş: yalnız xəbər sahibinə (əgər xəbərə bağlıdırsa)
        if room.news_id:
            news = News.query.get(room.news_id)
            if news and news.author_id and news.author_id != current_user.id:
                author = User.query.get(news.author_id)
                if author:
                    add_notification(author, f"{current_user.username} '{news.title}' xəbəri üçün müzakirə otağı yaratdı.")
        return redirect(url_for('community'))

@app.route('/room/<int:room_id>')
def room(room_id):
    room = Room.query.get_or_404(room_id)
    posts = Post.query.filter_by(room_id=room_id).order_by(Post.created_at.asc()).all()
    return render_template('room.html', room=room, posts=posts)

@app.route('/post/<int:room_id>', methods=['POST'])
@login_required
def add_post(room_id):
    content = request.form.get('content', '').strip()
    is_spoiler = request.form.get('is_spoiler') == '1'
    if not content:
        return redirect(url_for('room', room_id=room_id))
    post = Post(room_id=room_id, user_id=current_user.id, content=content, is_spoiler=is_spoiler)
    db.session.add(post)
    db.session.commit()
    add_xp(current_user, 5)
    update_quest_progress(current_user, 'post', 1)
    check_achievements(current_user)
        # Yalnız otaq sahibinə bildiriş göndər (özü deyilsə)
    room = Room.query.get(room_id)
    if room and room.creator_id != current_user.id:
        room_owner = User.query.get(room.creator_id)
        if room_owner:
            add_notification(room_owner, f"{current_user.username} '{room.name}' otağında yeni mesaj yazdı.")
    return redirect(url_for('room', room_id=room_id))

@app.route('/report/submit', methods=['POST'])
@login_required
def report_submit():
    target_type = request.form.get('target_type')
    target_id = int(request.form.get('target_id'))
    reason = request.form.get('reason', '')
    if target_type not in ['post', 'room']:
        flash('Səhv şikayət növü.')
        return redirect(request.referrer or url_for('index'))
    report = Report(reporter_id=current_user.id, target_type=target_type, target_id=target_id, reason=reason)
    db.session.add(report)
    db.session.commit()
    flash('Şikayət göndərildi.')
    return redirect(request.referrer or url_for('index'))

@app.route('/report/post/<int:post_id>', methods=['POST'])
@login_required
def report_post(post_id):
    post = Post.query.get_or_404(post_id)
    reason = request.form.get('reason', '')
    report = Report(reporter_id=current_user.id, target_type='post', target_id=post.id, reason=reason)
    db.session.add(report)
    db.session.commit()
    flash('Şikayət göndərildi.')
    return redirect(request.referrer or url_for('index'))

@app.route('/report/room/<int:room_id>', methods=['POST'])
@login_required
def report_room(room_id):
    room = Room.query.get_or_404(room_id)
    reason = request.form.get('reason', '')
    report = Report(reporter_id=current_user.id, target_type='room', target_id=room.id, reason=reason)
    db.session.add(report)
    db.session.commit()
    flash('Şikayət göndərildi.')
    return redirect(request.referrer or url_for('index'))

@app.route('/like-news/<int:news_id>', methods=['POST'])
@login_required
def like_news(news_id):
    news = News.query.get_or_404(news_id)
    existing_like = NewsLike.query.filter_by(user_id=current_user.id, news_id=news.id).first()
    if existing_like:
        # Bəyənməni geri al
        db.session.delete(existing_like)
        news.likes = max(0, news.likes - 1)
        db.session.commit()
        flash('Bəyənmə geri alındı.')
    else:
        # Yeni bəyənmə
        like = NewsLike(user_id=current_user.id, news_id=news.id)
        db.session.add(like)
        news.likes += 1
        db.session.commit()
        # XP və görəvlər
        add_xp(current_user, 1)
        update_quest_progress(current_user, 'like', 1)
        check_achievements(current_user)
        # Bildiriş: yalnız xəbər sahibinə (əgər admin deyilsə və xəbərin müəllifi varsa)
        if news.author_id and news.author_id != current_user.id:
            author = User.query.get(news.author_id)
            if author:
                add_notification(author, f"{current_user.username} sizin '{news.title}' xəbərinizi bəyəndi.")
        else:
            # Öz xəbərini bəyənəndə bildiriş getməsin
            pass
    return redirect(url_for('news_detail', news_id=news.id))

# ---------- AUTH ----------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        if not username or not password:
            flash('İstifadəçi adı və şifrə məcburidir')
            return redirect(url_for('register'))
        if not is_strong_password(password):
            flash('Şifrə ən az 8 simvol, hərf və rəqəm olmalıdır')
            return redirect(url_for('register'))
        if email and not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email):
            flash('Email formatı düzgün deyil')
            return redirect(url_for('register'))
        if User.query.filter_by(username=username).first():
            flash('Bu istifadəçi adı artıq mövcuddur')
            return redirect(url_for('register'))
        if email and User.query.filter_by(email=email).first():
            flash('Bu email artıq qeydiyyatdan keçib')
            return redirect(url_for('register'))
        user = User(username=username, email=email, password_hash=generate_password_hash(password))
        db.session.add(user)
        db.session.commit()
        login_user(user)
        start_title = Title.query.filter_by(name="Başlanğıc").first()
        if start_title:
            user.title_id = start_title.id
            ut = UserTitle(user_id=user.id, title_id=start_title.id)
            db.session.add(ut)
            db.session.commit()
        return redirect(url_for('index'))
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head><title>Qeydiyyat</title></head>
    <body>
        <h1>Qeydiyyat</h1>
        <form method="POST">
            <input type="text" name="username" placeholder="İstifadəçi adı" required><br>
            <input type="email" name="email" placeholder="Email" required><br>
            <input type="password" name="password" placeholder="Şifrə (ən az 8 simvol)" required><br>
            <button type="submit">Qeydiyyatdan keç</button>
        </form>
    </body>
    </html>
    ''')

@app.route('/login', methods=['POST'])
@limiter.limit("5 per minute")
def login():
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')
    user = User.query.filter_by(username=username).first()
    if user and check_password_hash(user.password_hash, password):
        if user.is_banned:
            if user.banned_until and user.banned_until < datetime.now():
                user.is_banned = False
                user.banned_until = None
                user.banned_reason = ''
                db.session.commit()
            else:
                flash('Hesabınız banlandı.')
                return redirect(url_for('index'))
        login_user(user)
        return redirect(url_for('index'))
    flash('İstifadəçi adı və ya şifrə yanlışdır')
    return redirect(url_for('index'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/profile')
@login_required
def profile():
    claimed_today = (current_user.last_login_date == date.today().isoformat())
    reset_user_quests(current_user)
    daily_quests = Quest.query.filter_by(is_daily=True).all()
    weekly_quests = Quest.query.filter_by(is_weekly=True).all()
    user_quests = {}
    for uq in current_user.quests:
        user_quests[uq.quest_id] = uq
    all_achievements = Achievement.query.all()
    earned_ids = [ua.achievement_id for ua in current_user.achievements]
    earned_achievements = {ach.id: (ach.id in earned_ids) for ach in all_achievements}
    earned_titles = get_earned_titles(current_user)
    return render_template('profile.html',
                           claimed_today=claimed_today,
                           daily_quests=daily_quests,
                           weekly_quests=weekly_quests,
                           user_quests=user_quests,
                           all_achievements=all_achievements,
                           earned_achievements=earned_achievements,
                           earned_titles=earned_titles)
@app.route('/profile/update-bio', methods=['POST'])
@login_required
def update_bio():
    current_user.bio = request.form.get('bio', '').strip()
    current_user.twitter_link = request.form.get('twitter_link', '').strip()
    current_user.instagram_link = request.form.get('instagram_link', '').strip()
    current_user.discord_link = request.form.get('discord_link', '').strip()
    db.session.commit()
    flash('Profil yeniləndi')
    return redirect(url_for('profile'))

@app.route('/profile/change-password', methods=['POST'])
@login_required
def change_password():
    current_password = request.form.get('current_password', '')
    new_password = request.form.get('new_password', '')
    confirm_password = request.form.get('confirm_password', '')
    if not check_password_hash(current_user.password_hash, current_password):
        flash('Hazırkı şifrə yanlışdır')
    elif new_password != confirm_password:
        flash('Yeni şifrələr uyğun gəlmir')
    elif not is_strong_password(new_password):
        flash('Şifrə ən az 8 simvol, hərf və rəqəm olmalıdır')
    else:
        current_user.password_hash = generate_password_hash(new_password)
        db.session.commit()
        flash('Şifrə yeniləndi')
    return redirect(url_for('profile'))

@app.route('/profile/set-active-title/<int:title_id>', methods=['POST'])
@login_required
def set_active_title(title_id):
    title = Title.query.get_or_404(title_id)
    if UserTitle.query.filter_by(user_id=current_user.id, title_id=title.id).first():
        current_user.title_id = title.id
        db.session.commit()
        flash(f"Aktiv ünvan: {title.name}")
    else:
        flash("Bu ünvana sahib deyilsiniz.")
    return redirect(url_for('profile'))

@app.route('/profile/set-showcase', methods=['POST'])
@login_required
def set_showcase():
    s1 = request.form.get('showcase1', '')
    s2 = request.form.get('showcase2', '')
    s3 = request.form.get('showcase3', '')
    current_user.showcase1_id = int(s1) if s1 else None
    current_user.showcase2_id = int(s2) if s2 else None
    current_user.showcase3_id = int(s3) if s3 else None
    db.session.commit()
    flash("Vitrin yeniləndi")
    return redirect(url_for('profile'))

@app.route('/claim-daily', methods=['POST'])
@login_required
def claim_daily():
    if daily_reward(current_user):
        flash('Günlük ödül alındı!')
    else:
        flash('Bu gün artıq ödül almısınız.')
    return redirect(url_for('profile'))

@app.route('/upload-avatar', methods=['POST'])
@login_required
def upload_avatar():
    if 'avatar' not in request.files:
        flash('Fayl seçilməyib')
        return redirect(url_for('profile'))
    file = request.files['avatar']
    if file.filename == '':
        flash('Fayl seçilməyib')
        return redirect(url_for('profile'))
    if file:
        ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
        if ext not in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
            flash('Yalnız şəkil faylları yükləyə bilərsiniz')
            return redirect(url_for('profile'))
        filename = f"{current_user.id}_{datetime.utcnow().timestamp()}.{ext}"
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        current_user.avatar = filename
        db.session.commit()
        flash('Profil şəkli yeniləndi')
    return redirect(url_for('profile'))

# ---------- NOTIFICATIONS ----------
@app.route('/notifications', methods=['GET', 'POST'])
@login_required
def notifications():
    notifs = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).all()
    return render_template('notifications.html', notifications=notifs)

@app.route('/notifications/mark-read/<int:notif_id>')
@login_required
def mark_read(notif_id):
    notif = Notification.query.get_or_404(notif_id)
    if notif.user_id == current_user.id:
        notif.is_read = True
        db.session.commit()
    return redirect(url_for('notifications'))

@app.route('/notifications/mark-all-read')
@login_required
def mark_all_read():
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update({'is_read': True})
    db.session.commit()
    flash("Bütün bildirişlər oxunmuş işarələndi")
    return redirect(url_for('notifications'))

# ---------- ADMIN ----------
@app.route('/admin')
@login_required
@admin_required
def admin():
    all_news = News.query.filter_by(status='published').all()
    draft_news = News.query.filter_by(status='draft').all()
    all_manga = Manga.query.all()
    all_users = User.query.all()
    reports = Report.query.filter_by(handled=False).all()
    report_details = []
    for report in reports:
        if report.target_type == 'post':
            target = Post.query.get(report.target_id)
            content_snippet = target.content[:100] if target else 'Silinmiş'
            link = url_for('room', room_id=target.room_id) if target else '#'
        elif report.target_type == 'room':
            target = Room.query.get(report.target_id)
            content_snippet = target.name if target else 'Silinmiş'
            link = url_for('room', room_id=report.target_id) if target else '#'
        else:
            content_snippet = ''
            link = '#'
        report_details.append({'report': report, 'snippet': content_snippet, 'link': link})
    return render_template('admin.html', all_news=all_news, draft_news=draft_news, all_manga=all_manga, all_users=all_users, report_details=report_details)

@app.route('/admin/fetch-news')
@login_required
@admin_required
def fetch_news():
    articles = fetch_and_generate_news()
    count = 0
    for art in articles:
        title = art.get('title', 'Xəbər')
        content = art.get('content', '')
        category = art.get('category', 'Ümumi')
        source_url = art.get('source_url', '')
        image_keywords = art.get('image_search_keywords', title)
        image_url = art.get('image_url', '')
        if not image_url:
            image_url = get_image_url(image_keywords)
        if title and content:
            news = News(
                title=title,
                content=content,
                category=category,
                image_url=image_url,
                author_id=current_user.id,
                status='draft'
            )
            db.session.add(news)
            count += 1
    db.session.commit()
    flash(f"{count} xəbər qaralama olaraq əlavə edildi.")
    return redirect(url_for('admin'))

@app.route('/admin/generate-listicle', methods=['POST'])
@login_required
@admin_required
def admin_generate_listicle():
    topic = request.form.get('topic', '').strip()
    if not topic:
        flash('Mövzu daxil edin')
        return redirect(url_for('admin'))
    article = generate_listicle(topic)
    if article:
        title = article.get('title', topic)
        content = article.get('content', '')
        category = article.get('category', 'Ümumi')
        image_keywords = article.get('image_search_keywords', title)
        image_url = get_image_url(image_keywords)
        news = News(
            title=title,
            content=content,
            category=category,
            image_url=image_url,
            author_id=current_user.id,
            status='draft'
        )
        db.session.add(news)
        db.session.commit()
        flash('Siyahı məqaləsi qaralama olaraq yaradıldı.')
    else:
        flash('Məqalə yaradıla bilmədi, agent boş nəticə qaytardı.')
    return redirect(url_for('admin'))

@app.route('/admin/add-news', methods=['POST'])
@login_required
@admin_required
def add_news():
    title = request.form.get('title', '').strip()
    content = request.form.get('content', '').strip()
    category = request.form.get('category', 'Ümumi').strip()
    image_url = request.form.get('image_url', '').strip()
    image_file = request.files.get('image_file')
    if image_file and image_file.filename != '':
        filename = process_image(image_file, 800, 500)
        if filename:
            image_url = filename
    if title and content:
        if not image_url:
            image_url = get_image_url(title)
        news = News(title=title, content=content, category=category, image_url=image_url, author_id=current_user.id)
        db.session.add(news)
        db.session.commit()

        # Blokları əlavə et
        block_types = request.form.getlist('block_type')
        block_texts = request.form.getlist('block_text')
        block_image_urls = request.form.getlist('block_image_url')
        block_image_files = request.files.getlist('block_image_file')
        block_layouts = request.form.getlist('block_layout')

        for i in range(len(block_types)):
            btype = block_types[i]
            text_content = block_texts[i] if i < len(block_texts) else ''
            image_url_block = block_image_urls[i] if i < len(block_image_urls) else ''
            layout = block_layouts[i] if i < len(block_layouts) else 'stack'
            if btype == 'image':
                if i < len(block_image_files):
                    file = block_image_files[i]
                    if file and file.filename != '':
                        fname = process_image(file, 800, 500)
                        if fname:
                            image_url_block = fname
            if btype in ['text', 'image']:
                block = NewsBlock(
                    news_id=news.id,
                    block_type=btype,
                    text_content=text_content,
                    image_url=image_url_block,
                    layout=layout,
                    order=i
                )
                db.session.add(block)
        db.session.commit()
    return redirect(url_for('admin'))
@app.route('/admin/ban-user/<int:user_id>')
@login_required
@admin_required
def ban_user(user_id):
    user = User.query.get_or_404(user_id)
    duration = request.args.get('duration', '1')
    if duration == 'forever':
        user.banned_until = None
        user.is_banned = True
    else:
        days = int(duration)
        user.banned_until = datetime.now() + timedelta(days=days)
        user.is_banned = True
    user.banned_reason = 'Admin tərəfindən banlandı'
    db.session.commit()
    flash(f"{user.username} banlandı.")
    return redirect(url_for('admin'))

@app.route('/admin/mute-user/<int:user_id>')
@login_required
@admin_required
def mute_user(user_id):
    user = User.query.get_or_404(user_id)
    duration = request.args.get('duration', '1')
    if duration == 'forever':
        user.muted_until = None
        user.is_muted = True
    else:
        days = int(duration)
        user.muted_until = datetime.now() + timedelta(days=days)
        user.is_muted = True
    user.muted_reason = 'Admin tərəfindən susturuldu'
    db.session.commit()
    flash(f"{user.username} susturuldu.")
    return redirect(url_for('admin'))

@app.route('/admin/unban-user/<int:user_id>')
@login_required
@admin_required
def unban_user(user_id):
    user = User.query.get_or_404(user_id)
    user.is_banned = False
    user.banned_until = None
    user.banned_reason = ''
    db.session.commit()
    flash(f"{user.username} banı açıldı.")
    return redirect(url_for('admin'))

@app.route('/admin/unmute-user/<int:user_id>')
@login_required
@admin_required
def unmute_user(user_id):
    user = User.query.get_or_404(user_id)
    user.is_muted = False
    user.muted_until = None
    user.muted_reason = ''
    db.session.commit()
    flash(f"{user.username} susturma açıldı.")
    return redirect(url_for('admin'))

@app.route('/admin/handle-report/<int:report_id>')
@login_required
@admin_required
def handle_report(report_id):
    report = Report.query.get_or_404(report_id)
    report.handled = True
    db.session.commit()
    flash("Şikayət həll edildi.")
    return redirect(url_for('admin'))

@app.route('/admin/delete-report/<int:report_id>')
@login_required
@admin_required
def delete_report(report_id):
    report = Report.query.get_or_404(report_id)
    db.session.delete(report)
    db.session.commit()
    flash("Şikayət silindi.")
    return redirect(url_for('admin'))

@app.route('/admin/edit-news/<int:news_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_news(news_id):
    news = News.query.get_or_404(news_id)
    if request.method == 'POST':
        news.title = request.form.get('title', '').strip()
        news.content = request.form.get('content', '').strip()
        news.category = request.form.get('category', 'Ümumi').strip()
        news.image_url = request.form.get('image_url', '').strip()
        image_file = request.files.get('image_file')
        if image_file and image_file.filename != '':
            filename = process_image(image_file, 800, 500)
            if filename:
                news.image_url = filename

        # Mövcud blokları sil
        NewsBlock.query.filter_by(news_id=news.id).delete()
        db.session.commit()

        # Yeni blokları əlavə et
        block_types = request.form.getlist('block_type')
        block_texts = request.form.getlist('block_text')
        block_image_urls = request.form.getlist('block_image_url')
        block_image_files = request.files.getlist('block_image_file')
        block_layouts = request.form.getlist('block_layout')

        for i in range(len(block_types)):
            btype = block_types[i]
            text_content = block_texts[i] if i < len(block_texts) else ''
            image_url = block_image_urls[i] if i < len(block_image_urls) else ''
            layout = block_layouts[i] if i < len(block_layouts) else 'stack'
            if btype == 'image':
                if i < len(block_image_files):
                    file = block_image_files[i]
                    if file and file.filename != '':
                        fname = process_image(file, 800, 500)
                        if fname:
                            image_url = fname
            if btype in ['text', 'image']:
                block = NewsBlock(
                    news_id=news.id,
                    block_type=btype,
                    text_content=text_content,
                    image_url=image_url,
                    layout=layout,
                    order=i
                )
                db.session.add(block)
        db.session.commit()
        flash('Xəbər yeniləndi')
        return redirect(url_for('admin'))
    return render_template('edit_news.html', news=news)

@app.route('/admin/edit-manga/<int:manga_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_manga(manga_id):
    manga = Manga.query.get_or_404(manga_id)
    if request.method == 'POST':
        manga.title = request.form.get('title', '').strip()
        manga.description = request.form.get('description', '').strip()
        manga.type = request.form.get('type', 'anime').strip()
        manga.cover_url = request.form.get('cover_url', '').strip()
        cover_file = request.files.get('cover_file')
        if cover_file and cover_file.filename != '':
            filename = process_image(cover_file, 400, 600)
            if filename:
                manga.cover_url = filename
        manga.rating = float(request.form.get('rating', 8.0))
        manga.status = request.form.get('status', 'Davam edir').strip()
        manga.chapters = int(request.form.get('chapters', 100))
        db.session.commit()
        flash('Manqa yeniləndi')
        return redirect(url_for('admin'))
    return render_template('edit_manga.html', manga=manga)

@app.route('/admin/add-manga', methods=['POST'])
@login_required
@admin_required
def add_manga():
    title = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    type_ = request.form.get('type', 'anime').strip()
    cover_url = request.form.get('cover_url', '').strip()
    cover_file = request.files.get('cover_file')
    rating = float(request.form.get('rating', 8.0))
    status = request.form.get('status', 'Davam edir').strip()
    chapters = int(request.form.get('chapters', 100))
    if cover_file and cover_file.filename != '':
        filename = process_image(cover_file, 400, 600)
        if filename:
            cover_url = filename
        else:
            flash('Şəkil formatı dəstəklənmir, URL istifadə ediləcək')
    if title and description:
        if not cover_url:
            cover_url = get_image_url(title)
        manga = Manga(title=title, description=description, type=type_, cover_url=cover_url, rating=rating, status=status, chapters=chapters)
        db.session.add(manga)
        db.session.commit()
    return redirect(url_for('admin'))

@app.route('/admin/publish-news/<int:news_id>')
@login_required
@admin_required
def publish_news(news_id):
    news = News.query.get_or_404(news_id)
    news.status = 'published'
    db.session.commit()
    flash('Məqalə yayımlandı.')
    return redirect(url_for('admin'))

@app.route('/admin/delete-news/<int:news_id>')
@login_required
@admin_required
def delete_news(news_id):
    news = News.query.get_or_404(news_id)
    # Bu xəbərə bağlı otaqların news_id-sini NULL et
    Room.query.filter_by(news_id=news.id).update({'news_id': None})
    # Xəbərə bağlı hesabatları sil (varsa)
    Report.query.filter_by(target_type='news', target_id=news.id).delete()
    db.session.delete(news)
    db.session.commit()
    flash('Xəbər silindi.')
    return redirect(url_for('admin'))

@app.route('/admin/delete-post/<int:post_id>')
@login_required
@admin_required
def admin_delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    user = post.user
    if user:
        add_notification(user, f"Sizin '{post.room.name}' otağındakı şərhiniz admin tərəfindən silindi.")
    room_id = post.room_id
    db.session.delete(post)
    db.session.commit()
    flash('Şərh silindi.')
    return redirect(request.referrer or url_for('room', room_id=room_id))

@app.route('/admin/clear-room-messages/<int:room_id>')
@login_required
@admin_required
def admin_clear_room_messages(room_id):
    room = Room.query.get_or_404(room_id)
    if room.name == 'Xəta Otağı':
        Post.query.filter_by(room_id=room.id).delete()
        db.session.commit()
        flash('Xəta Otağındakı bütün mesajlar silindi.')
    else:
        flash('Bu əməliyyat yalnız Xəta Otağı üçün keçərlidir.')
    return redirect(request.referrer or url_for('community'))

@app.route('/admin/delete-room/<int:room_id>')
@login_required
@admin_required
def admin_delete_room(room_id):
    room = Room.query.get_or_404(room_id)
    if room.name == 'Xəta Otağı':
        flash('Xəta Otağı silinə bilməz.')
        return redirect(request.referrer or url_for('community'))
    creator = room.creator
    if creator:
        add_notification(creator, f"Sizin '{room.name}' otağınız admin tərəfindən silindi.")
    Post.query.filter_by(room_id=room.id).delete()
    db.session.delete(room)
    db.session.commit()
    flash('Otaq silindi.')
    return redirect(request.referrer or url_for('community'))

@app.route('/admin/clear-all-posts')
@login_required
@admin_required
def clear_all_posts():
    Post.query.delete()
    db.session.commit()
    flash('Bütün şərhlər silindi.')
    return redirect(url_for('admin'))

@app.route('/admin/delete-manga/<int:manga_id>')
@login_required
@admin_required
def delete_manga(manga_id):
    manga = Manga.query.get_or_404(manga_id)
    db.session.delete(manga)
    db.session.commit()
    return redirect(url_for('admin'))

# ---------- INIT ----------
def init_db():
    with app.app_context():
        db.create_all()
        try:
            db.session.execute("ALTER TABLE title ADD COLUMN required_xp INTEGER DEFAULT 0")
            db.session.commit()
        except:
            db.session.rollback()

        try:
            db.session.execute("ALTER TABLE news ADD COLUMN status VARCHAR(20) DEFAULT 'draft'")
            db.session.commit()
        except:
            db.session.rollback()

        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', email='admin@midigitalverse.com', password_hash=generate_password_hash('MiriMID26&'), is_admin=True, points=100)
            db.session.add(admin)
            db.session.commit()
            print("Admin istifadəçi yaradıldı: admin / admin123")
        admin = User.query.filter_by(username='admin').first()
        admin_title = Title.query.filter_by(name="Admin").first()
        if admin_title:
            admin.title_id = admin_title.id
            db.session.commit()
        if News.query.count() == 0 and Manga.query.count() == 0:
            print("İlkin məzmun yaradılır...")
            news_items = generate_news_content()
            for item in news_items:
                image_url = item.get('image_url', '')
                if not image_url:
                    image_url = get_image_url(item.get('title', ''))
                news = News(title=item.get('title', 'Xəbər'), content=item.get('content', ''), category=item.get('category', 'Ümumi'), image_url=image_url)
                db.session.add(news)
            manga_items = generate_manga_content()
            for item in manga_items:
                cover_url = item.get('cover_url', '')
                if not cover_url:
                    cover_url = get_image_url(item.get('title', ''))
                manga = Manga(title=item.get('title', 'Manqa'), description=item.get('description', ''), type=item.get('type', 'anime'), cover_url=cover_url, rating=float(item.get('rating', 8.0)), status=item.get('status', 'Davam edir'), chapters=int(item.get('chapters', 100)))
                db.session.add(manga)
            db.session.commit()
            print("İlkin məzmun bazaya yazıldı.")
        seed_titles()
        seed_quests_and_achievements()
        if Room.query.filter_by(name="Xəta Otağı").first() is None:
            error_room = Room(name="Xəta Otağı", news_id=None, creator_id=admin.id)
            db.session.add(error_room)
            db.session.commit()
            print("Xəta Otağı yaradıldı.")

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)