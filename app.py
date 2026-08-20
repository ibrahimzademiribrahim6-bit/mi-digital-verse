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

from models import db, User, News, Manga, Room, Post, Title, UserTitle, Achievement, UserAchievement, Notification, Quest, UserQuest, Report, NewsBlock, NewsLike, Comment
from content_generator import generate_news_content, generate_manga_content, get_image_url, fetch_and_generate_news, generate_listicle

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'gizli-acar-12345')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 8 * 1024 * 1024  # 8 MB
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = True   # PythonAnywhere HTTPS olduÄŸu Ã¼Ã§Ã¼n tÉ™hlÃ¼kÉ™sizdir
app.config['REMEMBER_COOKIE_HTTPONLY'] = True
app.config['REMEMBER_COOKIE_SECURE'] = True
app.config['REMEMBER_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_NAME'] = 'midigitalverse_session'

db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'ZÉ™hmÉ™t olmasa giriÅŸ edin.'

@login_manager.unauthorized_handler
def unauthorized():
    flash(_t('ZÉ™hmÉ™t olmasa giriÅŸ edin.', 'Please log in.'))
    return redirect(url_for('index'))

Talisman(app, content_security_policy=None, force_https=True)
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def _t(az_text, en_text):
    lang = session.get('lang', 'az')
    return az_text if lang == 'az' else en_text

@app.before_request
def check_banned_user():
    if current_user.is_authenticated:
        if current_user.is_banned:
            if current_user.banned_until and current_user.banned_until < datetime.now():
                # Ban mÃ¼ddÉ™ti bitib, azad et
                current_user.is_banned = False
                current_user.banned_until = None
                current_user.banned_reason = ''
                db.session.commit()
            else:
                logout_user()
                flash(_t('HesabÄ±nÄ±z banlandÄ±. SÉ™bÉ™b: ', 'Your account has been banned. Reason: ') + (current_user.banned_reason or _t('GÃ¶stÉ™rilmÉ™yib', 'Not specified')))
                return redirect(url_for('index'))

@app.before_request
def set_user_title():
    if current_user.is_authenticated:
        update_user_title(current_user)

@app.before_request
def set_language():
    lang = request.args.get('lang')
    if lang in ['az', 'en']:
        session['lang'] = lang
    if 'lang' not in session:
        session['lang'] = 'az'

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
    add_notification(user, f"GÃ¼nlÃ¼k giriÅŸ Ã¶dÃ¼lÃ¼: +{bonus} XP")
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
        print(f"ÅžÉ™kil emalÄ± xÉ™tasÄ±: {e}")
        return None

def process_blocks(request, news_id):
    block_types = request.form.getlist('block_type')
    block_titles_az = request.form.getlist('block_title_az')
    block_titles_en = request.form.getlist('block_title_en')
    block_texts_az = request.form.getlist('block_text_az')
    block_texts_en = request.form.getlist('block_text_en')
    block_image_urls = request.form.getlist('block_image_url')
    block_image_files = request.files.getlist('block_image_file')
    block_layouts = request.form.getlist('block_layout')

    for i in range(len(block_types)):
        btype = block_types[i]
        title_az = block_titles_az[i] if i < len(block_titles_az) else ''
        title_en = block_titles_en[i] if i < len(block_titles_en) else ''
        text_az = block_texts_az[i] if i < len(block_texts_az) else ''
        text_en = block_texts_en[i] if i < len(block_texts_en) else ''
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
                news_id=news_id,
                block_type=btype,
                title_az=title_az,
                title_en=title_en,
                text_content_az=text_az,
                text_content_en=text_en,
                image_url=image_url,
                layout=layout,
                order=i
            )
            db.session.add(block)

# ---------- Bonus hesablanmasÄ± ----------
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

# ---------- Ãœnvan sisteminin yenilÉ™nmÉ™si ----------
def seed_titles():
    if Title.query.count() > 0:
        return
    # AÄŸ (20)
    white_titles = [
        ("BaÅŸlanÄŸÄ±c", "Ä°lk addÄ±m"),
        ("Ä°lk AddÄ±m", "Saytda ilk fÉ™aliyyÉ™t"),
        ("Oxucu", "Ä°lk xÉ™bÉ™ri oxu"),
        ("Ä°zlÉ™yici", "Ä°lk manqa/animeni izlÉ™"),
        ("MaraqlÄ±", "5 xÉ™bÉ™r oxu"),
        ("NaÅŸÄ±", "10 XP topla"),
        ("PÉ™rÉ™stiÅŸkar", "3 gÃ¼n ardÄ±cÄ±l giriÅŸ"),
        ("Sadiq", "7 gÃ¼n ardÄ±cÄ±l giriÅŸ"),
        ("Aktiv", "5 ÅŸÉ™rh yaz"),
        ("Daimi", "10 ÅŸÉ™rh yaz"),
        ("GÉ™nc QÉ™hrÉ™man", "25 bÉ™yÉ™nmÉ™ et"),
        ("TÉ™dqiqatÃ§Ä±", "3 mÃ¼xtÉ™lif otaqda ÅŸÉ™rh yaz"),
        ("SÉ™yyah", "5 mÃ¼xtÉ™lif otaqda ÅŸÉ™rh yaz"),
        ("MÃ¼ÅŸahidÉ™Ã§i", "10 xÉ™bÉ™r oxu"),
        ("NaÄŸÄ±lÃ§Ä±", "1 mÃ¼zakirÉ™ otaÄŸÄ± yarat"),
        ("YolÃ§u", "20 xÉ™bÉ™r oxu"),
        ("KÉ™ÅŸfiyyatÃ§Ä±", "50 bÉ™yÉ™nmÉ™ et"),
        ("Dost", "2 nailiyyÉ™t qazan"),
        ("Ä°lk Vitrin", "Ä°lk Ã¼nvanÄ± vitrinÉ™ É™lavÉ™ et"),
        ("Sadiq Oxucu", "30 xÉ™bÉ™r oxu"),
    ]
    # YaÅŸÄ±l (18)
    green_titles = [
        ("TÉ™crÃ¼bÉ™li", "100 XP topla"),
        ("Bilikli", "50 xÉ™bÉ™r oxu"),
        ("SÃ¼rÉ™tli", "3 gÃ¼nlÃ¼k giriÅŸ seriyasÄ±"),
        ("Ã‡evik", "7 gÃ¼nlÃ¼k giriÅŸ seriyasÄ±"),
        ("Usta TÉ™lÉ™bÉ™", "100 bÉ™yÉ™nmÉ™ et"),
        ("Gizli GÉ™zÉ™n", "10 mÃ¼xtÉ™lif otaqda ÅŸÉ™rh yaz"),
        ("Anime OvÃ§usu", "5 anime manqasÄ± oxu"),
        ("Manhwa KÉ™ÅŸfiyyatÃ§Ä±sÄ±", "5 manhwa oxu"),
        ("Manga Bilici", "5 manga oxu"),
        ("Webtoon HÉ™vÉ™skarÄ±", "5 webtoon oxu"),
        ("SÉ™hnÉ™ UstasÄ±", "5 mÃ¼zakirÉ™ otaÄŸÄ± yarat"),
        ("DÃ¶yÃ¼ÅŸÃ§Ã¼", "200 XP topla"),
        ("Sadiq Ä°zlÉ™yici", "14 gÃ¼nlÃ¼k giriÅŸ seriyasÄ±"),
        ("SÉ™sli", "50 ÅŸÉ™rh yaz"),
        ("Ä°namlÄ±", "300 XP topla"),
        ("CanlÄ±", "100 xÉ™bÉ™r oxu"),
        ("Ulduz", "3 nailiyyÉ™t qazan"),
        ("Veteran", "400 XP topla"),
    ]
    # Mavi (16)
    blue_titles = [
        ("Usta", "500 XP topla"),
        ("Veteran", "700 XP topla"),
        ("Strateq", "300 bÉ™yÉ™nmÉ™ et"),
        ("DÃ¶yÃ¼ÅŸÃ§Ã¼", "30 gÃ¼nlÃ¼k giriÅŸ seriyasÄ±"),
        ("ÆfsanÉ™vi OvÃ§u", "20 mÃ¼xtÉ™lif otaqda ÅŸÉ™rh yaz"),
        ("QaranlÄ±q CÉ™ngavÉ™r", "1000 XP topla"),
        ("Neon QÄ±lÄ±nc", "1500 XP topla"),
        ("SÉ™viyyÉ™ AtÄ±cÄ±sÄ±", "10 nailiyyÉ™t qazan"),
        ("Manhva Lordu", "50 manhwa oxu"),
        ("Anime SenpaysÄ±", "50 anime izlÉ™"),
        ("Manga HÉ™kimi", "50 manga oxu"),
        ("Webtoon UstasÄ±", "50 webtoon oxu"),
        ("Sadiq MÃ¼zakirÉ™Ã§i", "20 mÃ¼zakirÉ™ otaÄŸÄ± yarat"),
        ("SÉ™s KralÄ±", "200 ÅŸÉ™rh yaz"),
        ("XÉ™bÉ™r CanavarÄ±", "200 xÉ™bÉ™r oxu"),
        ("Ä°ÅŸÄ±q SÃ¼rÉ™ti", "500 bÉ™yÉ™nmÉ™ et"),
    ]
    # BÉ™nÃ¶vÅŸÉ™yi (12) - gizli, xÃ¼susi ÅŸÉ™rtlÉ™r
    purple_titles = [
        ("Epik QÉ™hrÉ™man", "3000 XP + 50 xÉ™bÉ™r + 5 nailiyyÉ™t", "purple", True, "xp", 3000),
        ("ÆfsanÉ™vi GÃ¶zÉ™tÃ§i", "3500 XP + 100 xÉ™bÉ™r + 7 nailiyyÉ™t", "purple", True, "xp", 3500),
        ("Buz DÃ¶yÃ¼ÅŸÃ§Ã¼sÃ¼", "4000 XP + 20 mÃ¼xtÉ™lif otaqda ÅŸÉ™rh", "purple", True, "xp", 4000),
        ("Alov Ruhu", "4500 XP + 30 gÃ¼nlÃ¼k seriya", "purple", True, "xp", 4500),
        ("KÃ¶lgÉ™ UstasÄ±", "5000 XP + 150 xÉ™bÉ™r", "purple", True, "xp", 5000),
        ("SÉ™ma PÉ™rÉ™stiÅŸkarÄ±", "5500 XP + 10 mÃ¼zakirÉ™ otaÄŸÄ±", "purple", True, "xp", 5500),
        ("Titan", "6000 XP + 500 bÉ™yÉ™nmÉ™", "purple", True, "xp", 6000),
        ("DÉ™rviÅŸ", "6500 XP + 30 nailiyyÉ™t", "purple", True, "xp", 6500),
        ("FÄ±rtÄ±na Ã‡aÄŸÄ±ran", "7000 XP + 300 xÉ™bÉ™r", "purple", True, "xp", 7000),
        ("ZamansÄ±z", "7500 XP + 40 gÃ¼nlÃ¼k seriya", "purple", True, "xp", 7500),
        ("Ã–lÃ¼msÃ¼z", "8000 XP + 600 bÉ™yÉ™nmÉ™", "purple", True, "xp", 8000),
        ("Kosmik SÉ™yyah", "8500 XP + 100 mÃ¼xtÉ™lif otaqda ÅŸÉ™rh", "purple", True, "xp", 8500),
    ]
    # SarÄ± (7) - É™fsanÉ™vi, hÉ™r biri yalnÄ±z bir nÉ™fÉ™rÉ™
    legendary_titles = [
        ("Ä°lk Toxum", "10000 XP + 100 gÃ¼nlÃ¼k seriya + 10 nailiyyÉ™t + 200 xÉ™bÉ™r + 100 bÉ™yÉ™nmÉ™", "yellow", True, "xp", 10000),
        ("TanrÄ± SÉ™viyyÉ™si", "12000 XP + 120 gÃ¼nlÃ¼k seriya + 12 nailiyyÉ™t + 300 xÉ™bÉ™r + 200 bÉ™yÉ™nmÉ™", "yellow", True, "xp", 12000),
        ("MÃ¼tlÉ™q GÃ¼c", "14000 XP + 150 gÃ¼nlÃ¼k seriya + 15 nailiyyÉ™t + 500 xÉ™bÉ™r + 500 bÉ™yÉ™nmÉ™", "yellow", True, "xp", 14000),
        ("Kainat HÃ¶kmdarÄ±", "16000 XP + 180 gÃ¼nlÃ¼k seriya + 20 nailiyyÉ™t + 800 xÉ™bÉ™r + 1000 bÉ™yÉ™nmÉ™", "yellow", True, "xp", 16000),
        ("Son Ãœmid", "18000 XP + 200 gÃ¼nlÃ¼k seriya + 25 nailiyyÉ™t + 1000 xÉ™bÉ™r + 2000 bÉ™yÉ™nmÉ™", "yellow", True, "xp", 18000),
        ("ÆbÉ™di ÆfsanÉ™", "20000 XP + 250 gÃ¼nlÃ¼k seriya + 30 nailiyyÉ™t + 1500 xÉ™bÉ™r + 5000 bÉ™yÉ™nmÉ™", "yellow", True, "xp", 20000),
        ("Ä°lk Toxum (Alternativ)", "Æsl É™fsanÉ™", "yellow", True, "xp", 99999),  # ehtiyat
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

    # Admin Ã¼nvanÄ±
    all_titles.append(Title(name="Admin", description="Sayt rÉ™hbÉ™ri", color="yellow", rarity="admin", hidden=False, condition_type="admin", condition_value=0))
    db.session.add_all(all_titles)
    db.session.commit()

def seed_quests_and_achievements():
    if Quest.query.count() == 0:
        quests = [
            Quest(name="GÃ¼ndÉ™lik Oxucu", description="1 xÉ™bÉ™r oxu", requirement_type="news_read", target_value=1, reward_xp=10, is_daily=True),
            Quest(name="GÃ¼ndÉ™lik BÉ™yÉ™nÉ™n", description="1 bÉ™yÉ™nmÉ™ et", requirement_type="like", target_value=1, reward_xp=5, is_daily=True),
            Quest(name="GÃ¼ndÉ™lik ÅžÉ™rhÃ§i", description="1 ÅŸÉ™rh yaz", requirement_type="post", target_value=1, reward_xp=10, is_daily=True),
            Quest(name="HÉ™ftÉ™lik MÉ™hsuldar", description="5 xÉ™bÉ™r oxu", requirement_type="news_read", target_value=5, reward_xp=30, is_weekly=True),
            Quest(name="HÉ™ftÉ™lik BÉ™yÉ™nÉ™n", description="5 bÉ™yÉ™nmÉ™ et", requirement_type="like", target_value=5, reward_xp=20, is_weekly=True),
            Quest(name="HÉ™ftÉ™lik Sosial", description="1 mÃ¼zakirÉ™ otaÄŸÄ± yarat", requirement_type="room_create", target_value=1, reward_xp=25, is_weekly=True),
        ]
        db.session.add_all(quests)

    if Achievement.query.count() == 0:
        achievements = [
            Achievement(name="Ä°lk AddÄ±m", description="Ä°lk xÉ™bÉ™ri oxu", badge_icon="ðŸ“°", requirement_type="news_read", requirement_value=1),
            Achievement(name="XÉ™bÉ™r CanavarÄ±", description="10 xÉ™bÉ™r oxu", badge_icon="ðŸ“š", requirement_type="news_read", requirement_value=10),
            Achievement(name="BÉ™yÉ™nmÉ™ UstasÄ±", description="5 bÉ™yÉ™nmÉ™ et", badge_icon="â¤ï¸", requirement_type="like", requirement_value=5),
            Achievement(name="ÅžÉ™rh MÃ¼tÉ™xÉ™ssisi", description="5 ÅŸÉ™rh yaz", badge_icon="ðŸ’¬", requirement_type="post", requirement_value=5),
            Achievement(name="Otaq Qurucusu", description="3 mÃ¼zakirÉ™ otaÄŸÄ± yarat", badge_icon="ðŸ ", requirement_type="room_create", requirement_value=3),
            Achievement(name="GÃ¼ndÉ™lik AsÄ±lÄ±lÄ±q", description="7 gÃ¼n ardÄ±cÄ±l giriÅŸ", badge_icon="ðŸ”¥", requirement_type="streak", requirement_value=7),
            Achievement(name="SÉ™ssiz QÉ™hrÉ™man", description="50 XP topla", badge_icon="ðŸ¤«", requirement_type="points", requirement_value=50, hidden=True),
            Achievement(name="ÆfsanÉ™vi KolleksiyaÃ§Ä±", description="100 XP topla", badge_icon="ðŸŒŸ", requirement_type="points", requirement_value=100, hidden=True),
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
            add_notification(user, f"GÃ¶rÉ™vi tamamladÄ±n: {quest.name} (+{earned_xp} XP)")
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
            add_notification(user, f"NailiyyÉ™t qazandÄ±n: {ach.name} {ach.badge_icon}")
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

    # Qeyri-gizli Ã¼nvanlarÄ± XP-yÉ™ gÃ¶rÉ™ sÄ±rala
    normal_titles = Title.query.filter_by(hidden=False).order_by(Title.required_xp.desc()).all()
    for title in normal_titles:
        if title.rarity in ('common', 'uncommon', 'rare'):
            if user.points >= title.required_xp:
                # UyÄŸun Ã¼nvanÄ± qazanmadÄ±sa É™lavÉ™ et
                if not UserTitle.query.filter_by(user_id=user.id, title_id=title.id).first():
                    user_title = UserTitle(user_id=user.id, title_id=title.id)
                    db.session.add(user_title)
                    db.session.commit()
                    add_notification(user, f"Yeni Ã¼nvan qazandÄ±n: {title.name}")
                # Aktiv Ã¼nvana tÉ™yin et (É™n yÃ¼ksÉ™k)
                if user.title_id != title.id:
                    user.title_id = title.id
                    db.session.commit()
                break

    # Gizli Epik Ã¼nvanlar Ã¼Ã§Ã¼n ÅŸÉ™rtlÉ™r (sadÉ™lÉ™ÅŸdirilmiÅŸ: yalnÄ±z XP + bÉ™zi ÅŸÉ™rtlÉ™r)
    epic_titles = Title.query.filter_by(rarity="epic", hidden=True).all()
    for title in epic_titles:
        if UserTitle.query.filter_by(user_id=user.id, title_id=title.id).first():
            continue
        # MÃ¼vÉ™qqÉ™ti sadÉ™ ÅŸÉ™rt: XP-yÉ™ gÃ¶rÉ™
        if user.points >= title.condition_value:
            user_title = UserTitle(user_id=user.id, title_id=title.id)
            db.session.add(user_title)
            db.session.commit()
            add_notification(user, f"Epik Ã¼nvan qazandÄ±n: {title.name}")
            if user.title_id != title.id:
                user.title_id = title.id
                db.session.commit()

    # ÆfsanÉ™vi Ã¼nvanlar (unique)
    legendaries = Title.query.filter_by(rarity="legendary", hidden=True).all()
    for title in legendaries:
        if UserTitle.query.filter_by(user_id=user.id, title_id=title.id).first():
            continue
        # ÆgÉ™r baÅŸqasÄ± alÄ±bsa, keÃ§
        if title.unique_legendary and UserTitle.query.filter_by(title_id=title.id).first():
            continue
        # ÅžÉ™rtlÉ™r (sadÉ™lÉ™ÅŸdirilmiÅŸ)
        if (user.points >= title.condition_value and user.streak >= 100):
            user_title = UserTitle(user_id=user.id, title_id=title.id)
            db.session.add(user_title)
            db.session.commit()
            add_notification(user, f"ÆfsanÉ™vi Ã¼nvan qazandÄ±n: {title.name}")
            if user.title_id != title.id:
                user.title_id = title.id
                db.session.commit()

def get_earned_titles(user):
    return user.user_titles

# ---------- HTML ÅžABLONLARI (É™vvÉ™lki kimi, lakin profilÉ™ Ã¼nvan idarÉ™si É™lavÉ™ olundu) ----------
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

        /* ===== IÅžIQLI REJIM (LIGHT MODE) ===== */
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
            background-color: #1f2937; /* TÃ¼nd boz - dÃ¼ymÉ™lÉ™r vÉ™ kartlar */
            color: #ffffff;
            border: 1px solid #374151;
        }
        html.light .bg-gray-700 {
            background-color: #e5e7eb; /* AÃ§Ä±q boz - inputlar */
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
        /* Mobil menyu vÉ™ dÃ¼ymÉ™lÉ™r Ã¼Ã§Ã¼n */
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
<a href="/" class="text-gray-300 hover:text-cyan-400">{{ 'Ana SÉ™hifÉ™' if current_lang == 'az' else 'Home' }}</a>
<a href="/archive" class="text-gray-300 hover:text-cyan-400">{{ 'Arxiv' if current_lang == 'az' else 'Archive' }}</a>
<a href="/community" class="text-gray-300 hover:text-cyan-400">{{ 'Ä°cma' if current_lang == 'az' else 'Community' }}</a>
<a href="/about" class="text-gray-300 hover:text-cyan-400">{{ 'HaqqÄ±mÄ±zda' if current_lang == 'az' else 'About' }}</a>
                    {% if current_user.is_authenticated %}
                    <a href="/profile" class="text-gray-300 hover:text-cyan-400">{{ 'Profil' if current_lang == 'az' else 'Profile' }}</a>
                    {% if current_user.is_admin %}
                    <a href="/admin" class="text-yellow-400 hover:text-yellow-300">Admin</a>
                    {% endif %}
                    <a href="/logout" class="text-red-400 hover:text-red-300">{{ 'Ã‡Ä±xÄ±ÅŸ' if current_lang == 'az' else 'Logout' }}</a>
                    {% else %}
                    <button onclick="document.getElementById('authModal').classList.remove('hidden')" class="text-cyan-400 hover:text-cyan-300">{{ 'GiriÅŸ / Qeydiyyat' if current_lang == 'az' else 'Sign In / Join' }}</button>
                    {% endif %}
                </div>
                <div class="flex items-center space-x-3">
                    <!-- AxtarÄ±ÅŸ yalnÄ±z masaÃ¼stÃ¼ -->
                    <a href="/archive" class="p-2 rounded bg-gray-800 text-white hidden md:inline-block">ðŸ”</a>
                    <!-- BildiriÅŸ zÉ™ngi hÉ™miÅŸÉ™ -->
                    <a href="/notifications" class="p-2 rounded bg-gray-800 text-white relative">
                        ðŸ””
                        <span id="notif-badge" class="absolute -top-1 -right-1 bg-red-500 text-white rounded-full px-1 text-xs {% if unread_notifications_count == 0 %}hidden{% endif %}">{{ unread_notifications_count }}</span>
                    </a>
                    <!-- Dil vÉ™ tema yalnÄ±z masaÃ¼stÃ¼ -->
                    <button id="langToggle" class="p-2 rounded bg-gray-800 text-white hidden md:inline-block" onclick="window.location.href='/set-language/{{ 'en' if current_lang == 'az' else 'az' }}'">{{ 'EN' if current_lang == 'az' else 'AZ' }}</button>
                    <button id="langToggleMobile" class="p-2 rounded bg-gray-800 text-white md:hidden" onclick="window.location.href='/set-language/{{ 'en' if current_lang == 'az' else 'az' }}'">{{ 'EN' if current_lang == 'az' else 'AZ' }}</button>
                    <button id="themeToggle" style="display:none;" class="p-2 rounded-full bg-gray-800 text-yellow-400 hidden md:inline-block">ðŸŒ™</button>
                    <!-- Mobil menyu dÃ¼ymÉ™si -->
                    <button id="mobileMenuBtn" class="md:hidden p-2 rounded bg-gray-800 text-white" onclick="var m=document.getElementById('mobileMenu'); m.style.display = (m.style.display === 'block' ? 'none' : 'block');">â˜°</button>
                </div>
            </div>
        </div>
        <div id="mobileMenu" class="hidden md:hidden bg-gray-900 px-4 pb-4 flex flex-col">            <a href="/" class="block py-2 text-gray-300">{{ 'Ana SÉ™hifÉ™' if current_lang == 'az' else 'Home' }}</a>
            <a href="/archive" class="block py-2 text-gray-300">{{ 'Arxiv' if current_lang == 'az' else 'Archive' }}</a>
            <a href="/community" class="block py-2 text-gray-300">{{ 'Ä°cma' if current_lang == 'az' else 'Community' }}</a>
            <a href="/about" class="block py-2 text-gray-300">{{ 'HaqqÄ±mÄ±zda' if current_lang == 'az' else 'About' }}</a>
            {% if current_user.is_authenticated %}
                <a href="/profile" class="block py-2 text-gray-300">{{ 'Profil' if current_lang == 'az' else 'Profile' }}</a>
                <a href="/logout" class="block py-2 text-red-400">{{ 'Ã‡Ä±xÄ±ÅŸ' if current_lang == 'az' else 'Logout' }}</a>
            {% else %}
                <button onclick="document.getElementById('authModal').classList.remove('hidden')" class="block py-2 text-cyan-400 w-full text-left">{{ 'GiriÅŸ / Qeydiyyat' if current_lang == 'az' else 'Sign In / Join' }}</button>
            {% endif %}
        </div>
    </nav>

    <div id="authModal" class="fixed inset-0 bg-black bg-opacity-70 hidden z-50 flex items-center justify-center p-4">
        <div class="bg-gray-800 rounded-lg p-6 w-full max-w-md relative">
            <button onclick="document.getElementById('authModal').classList.add('hidden')" class="absolute top-3 right-3 text-gray-400 text-2xl">&times;</button>
            <div class="flex justify-center mb-4 space-x-4">
<button id="loginTabBtn" onclick="document.getElementById('loginForm').classList.remove('hidden'); document.getElementById('registerForm').classList.add('hidden'); this.classList.add('text-cyan-400','border-cyan-400'); this.classList.remove('text-gray-400','border-transparent'); document.getElementById('registerTabBtn').classList.remove('text-purple-400','border-purple-400'); document.getElementById('registerTabBtn').classList.add('text-gray-400','border-transparent');" class="px-4 py-2 text-cyan-400 border-b-2 border-cyan-400">{{ 'GiriÅŸ' if current_lang == 'az' else 'Login' }}</button>
<button id="registerTabBtn" onclick="document.getElementById('registerForm').classList.remove('hidden'); document.getElementById('loginForm').classList.add('hidden'); this.classList.add('text-purple-400','border-purple-400'); this.classList.remove('text-gray-400','border-transparent'); document.getElementById('loginTabBtn').classList.remove('text-cyan-400','border-cyan-400'); document.getElementById('loginTabBtn').classList.add('text-gray-400','border-transparent');" class="px-4 py-2 text-gray-400 border-b-2 border-transparent">{{ 'Qeydiyyat' if current_lang == 'az' else 'Register' }}</button>
            </div>
            <form id="loginForm" action="/login" method="POST" class="space-y-3">
<input type="text" name="username" placeholder="{{ 'Ä°stifadÉ™Ã§i adÄ±' if current_lang == 'az' else 'Username' }}" required class="w-full p-2 rounded bg-gray-700 text-white">
<input type="password" name="password" placeholder="{{ 'ÅžifrÉ™' if current_lang == 'az' else 'Password' }}" required class="w-full p-2 rounded bg-gray-700 text-white">
<button type="submit" class="w-full py-2 bg-cyan-500 hover:bg-cyan-600 text-white rounded">{{ 'Daxil ol' if current_lang == 'az' else 'Sign In' }}</button>
            </form>
            <form id="registerForm" action="/register" method="POST" class="space-y-3 hidden">
<input type="text" name="username" placeholder="{{ 'Ä°stifadÉ™Ã§i adÄ±' if current_lang == 'az' else 'Username' }}" required class="w-full p-2 rounded bg-gray-700 text-white">
<input type="email" name="email" placeholder="{{ 'Email' if current_lang == 'az' else 'Email' }}" class="w-full p-2 rounded bg-gray-700 text-white">
<input type="password" name="password" placeholder="{{ 'ÅžifrÉ™ (É™n az 8 simvol)' if current_lang == 'az' else 'Password (at least 8 characters)' }}" required class="w-full p-2 rounded bg-gray-700 text-white">
<button type="submit" class="w-full py-2 bg-purple-500 hover:bg-purple-600 text-white rounded">{{ 'Qeydiyyatdan keÃ§' if current_lang == 'az' else 'Register' }}</button>
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
        <h3 class="text-xl font-bold mb-4">{{ 'ÅžikayÉ™t et' if current_lang == 'az' else 'Report' }}</h3>
        <form action="/report/submit" method="POST" class="space-y-3" onsubmit="return validateReportForm(this)" novalidate>
            <input type="hidden" name="target_type" id="reportTargetType">
            <input type="hidden" name="target_id" id="reportTargetId">
            <div>
                <label class="text-sm text-gray-400">{{ 'SÉ™bÉ™b' if current_lang == 'az' else 'Reason' }}</label>
                <select id="reportReasonSelect" name="reason" class="w-full p-2 rounded bg-gray-700 text-white" onchange="document.getElementById('otherReasonWrap').classList.toggle('hidden', this.value !== 'digÉ™r');">
                    <option value="">{{ 'SÉ™bÉ™b seÃ§in' if current_lang == 'az' else 'Select reason' }}</option>
                    <option value="sÃ¶yÃ¼ÅŸ">{{ 'SÃ¶yÃ¼ÅŸ' if current_lang == 'az' else 'Swearing' }}</option>
                    <option value="spoiler">{{ 'Spoiler paylaÅŸÄ±r' if current_lang == 'az' else 'Shares spoiler' }}</option>
                    <option value="tÉ™hqir">{{ 'TÉ™hqir edici' if current_lang == 'az' else 'Insulting' }}</option>
                    <option value="spam">Spam</option>
                    <option value="digÉ™r">{{ 'DigÉ™r' if current_lang == 'az' else 'Other' }}</option>
                </select>
            </div>
            <div id="otherReasonWrap" class="hidden mt-2">
                <label class="text-sm text-gray-400">{{ 'ÆlavÉ™ aÃ§Ä±qlama' if current_lang == 'az' else 'Additional details' }}</label>
                <textarea name="other_reason" class="w-full p-2 rounded bg-gray-700 text-white" rows="3"></textarea>
            </div>
            <button type="submit" class="w-full py-2 bg-red-500 hover:bg-red-600 text-white rounded">{{ 'GÃ¶ndÉ™r' if current_lang == 'az' else 'Submit' }}</button>
        </form>
    </div>
</div>
        {% block content %}{% endblock %}
    </main>

    <footer class="bg-gray-900 text-gray-400 py-6 border-t border-gray-700">
        <div class="max-w-7xl mx-auto text-center">
            <p>Â© {{ now.year }} Mi Digital Verse. BÃ¼tÃ¼n hÃ¼quqlar qorunur.</p>
        </div>
    </footer>
</div>

<script>
    const html = document.documentElement;
    html.classList.add('dark');
    html.classList.remove('light');
    
    // Tema vÉ™ Menyu
    document.getElementById('themeToggle')?.addEventListener('click', toggleTheme);
    document.getElementById('themeToggleMobile')?.addEventListener('click', toggleTheme);
    document.getElementById('mobileMenuBtn')?.addEventListener('click', () => {
        document.getElementById('mobileMenu').classList.toggle('hidden');
    });

    // Modallar
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

    // GiriÅŸ / Qeydiyyat TablarÄ±
    function showLogin() {
        document.getElementById('loginForm').classList.remove('hidden');
        document.getElementById('registerForm').classList.add('hidden');
        document.getElementById('loginTabBtn').classList.add('text-cyan-400', 'border-cyan-400');
        document.getElementById('loginTabBtn').classList.remove('text-gray-400', 'border-transparent');
        document.getElementById('registerTabBtn').classList.add('text-gray-400', 'border-transparent');
        document.getElementById('registerTabBtn').classList.remove('text-purple-400', 'border-purple-400');
    }
    
    function showRegister() {
        document.getElementById('registerForm').classList.remove('hidden');
        document.getElementById('loginForm').classList.add('hidden');
        document.getElementById('registerTabBtn').classList.add('text-purple-400', 'border-purple-400');
        document.getElementById('registerTabBtn').classList.remove('text-gray-400', 'border-transparent');
        document.getElementById('loginTabBtn').classList.add('text-gray-400', 'border-transparent');
        document.getElementById('loginTabBtn').classList.remove('text-cyan-400', 'border-cyan-400');
    }

    // Dil sistemi
    const translations = {
        az: { home: "Ana SÉ™hifÉ™", news: "XÉ™bÉ™rlÉ™r", library: "Kitabxana â–¾", community: "Ä°cma", about: "HaqqÄ±mÄ±zda", profile: "Profil", quests: "GÃ¶rÉ™vlÉ™r", achievements: "NailiyyÉ™tlÉ™r", admin: "Admin", logout: "Ã‡Ä±xÄ±ÅŸ", login: "GiriÅŸ / Qeydiyyat" },
        en: { home: "Home", news: "News", library: "Library â–¾", community: "Community", about: "About", profile: "Profile", quests: "Quests", achievements: "Achievements", admin: "Admin", logout: "Logout", login: "Sign In / Join" }
    };
    
    let currentLang = localStorage.getItem('lang') || '{{ current_lang }}' || 'az';
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
        const newLang = currentLang === 'az' ? 'en' : 'az';
        localStorage.setItem('lang', newLang);
        window.location.href = '/set-language/' + newLang;
    }
    
    document.getElementById('langToggle')?.addEventListener('click', toggleLanguage);
    document.getElementById('langToggleMobile')?.addEventListener('click', toggleLanguage);

    // ÅžikayÉ™t bÃ¶lmÉ™sindÉ™ "DigÉ™r" seÃ§imi
document.addEventListener('DOMContentLoaded', function() {
    const select = document.getElementById('reportReasonSelect');
    const otherWrap = document.getElementById('otherReasonWrap');
    if (select && otherWrap) {
        select.addEventListener('change', function() {
            if (this.value === 'digÉ™r') {
                otherWrap.classList.remove('hidden');
            } else {
                otherWrap.classList.add('hidden');
            }
        });
    }
});
</script>
<script>
(function() {
    setTimeout(function() {
        var flashItems = document.querySelectorAll('#flash-container .flash-item');
        flashItems.forEach(function(item) {
            item.style.transition = 'opacity 0.5s ease';
            item.style.opacity = '0';
            setTimeout(function() {
                item.remove();
            }, 500);
        });
    }, 5000);
})();

function validateReportForm(form) {
    const reasonSelect = document.getElementById('reportReasonSelect');
    if (!reasonSelect || reasonSelect.value === '') {
        alert("{{ 'ZÉ™hmÉ™t olmasa sÉ™bÉ™b seÃ§in.' if current_lang == 'az' else 'Please select a reason.' }}");
        return false;
    }
    return true;
}

</script>
</body>
</html>
"""

# DigÉ™r bÃ¼tÃ¼n ÅŸablonlar É™vvÉ™lki kimi qalÄ±r, lakin profil ÅŸablonunu yenilÉ™yirik.
INDEX_HTML = """
{% extends "base.html" %}
{% block title %}{{ 'Ana SÉ™hifÉ™' if current_lang == 'az' else 'Home' }} - Mi Digital Verse{% endblock %}
{% block content %}
<div class="max-w-7xl mx-auto px-4 py-8">
    <div class="hero-section rounded-xl p-8 mb-8 text-center">
        <h1 class="text-4xl md:text-5xl font-bold text-cyan-400 neon-text">{{ 'XoÅŸ gÉ™ldiniz!' if current_lang == 'az' else 'Welcome!' }}</h1>
        <p class="text-gray-300 mt-2">{{ 'Anime, manhwa, manhua vÉ™ oyun dÃ¼nyasÄ±nÄ±n É™n son xÉ™bÉ™rlÉ™ri' if current_lang == 'az' else 'The latest news from the world of anime, manhwa, manhua and games' }}</p>
    </div>
    <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div class="col-span-2">
            <h2 class="text-2xl font-semibold mb-4">{{ 'Son XÉ™bÉ™rlÉ™r' if current_lang == 'az' else 'Latest News' }}</h2>
            {% for news in latest_news %}
            <a href="/news/{{ news.id }}" class="block bg-gray-800 rounded-lg p-4 mb-4 card-glow">
                <h3 class="text-xl font-bold text-cyan-300">{{ get_lang_field(news, 'title') }}</h3>
                <p class="text-gray-400 text-sm">{{ news.published_at.strftime('%d.%m.%Y') }} | {{ news.category }}</p>
            </a>
            {% else %}
            <p>{{ 'HÉ™lÉ™ xÉ™bÉ™r yoxdur.' if current_lang == 'az' else 'No news yet.' }}</p>
            {% endfor %}
            <h2 class="text-2xl font-semibold mt-8 mb-4">{{ 'Æn Ã‡ox Oxunanlar' if current_lang == 'az' else 'Most Read' }}</h2>
            {% for news in most_read %}
            <a href="/news/{{ news.id }}" class="block bg-gray-800 rounded-lg p-4 mb-4 card-glow">
                <h3 class="text-xl font-bold text-cyan-300">{{ get_lang_field(news, 'title') }}</h3>
            <p class="text-gray-400">{{ news.category }} | {{ news.published_at.strftime('%d.%m.%Y') }} | {{ 'Oxunma:' if current_lang == 'az' else 'Views:' }} {{ news.views }}</p>
            </a>
            {% endfor %}
        </div>
        <div>
            <h2 class="text-2xl font-semibold mb-4">{{ 'SeÃ§ilmiÅŸ Manqa/Anime' if current_lang == 'az' else 'Featured Manga/Anime' }}</h2>
            {% for m in featured %}
            <a href="/manga/{{ m.id }}" class="block bg-gray-800 rounded-lg p-3 mb-3 card-glow flex items-center gap-3">
                <img src="{{ m.cover_url }}" alt="{{ m.title }}" class="w-16 h-24 object-cover rounded">
                <div>
                    <h3 class="font-bold">{{ m.title }}</h3>
                    <p class="text-sm text-gray-400">{{ m.type }}</p>
                    <p class="text-yellow-400">{{ 'Rating:' if current_lang == 'az' else 'Rating:' }} {{ m.rating }}</p>
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
{% block title %}{{ 'XÉ™bÉ™rlÉ™r' if current_lang == 'az' else 'News' }} - Mi Digital Verse{% endblock %}
{% block content %}
<div class="max-w-7xl mx-auto px-4 py-8">
    <h1 class="text-3xl font-bold mb-6">{{ 'XÉ™bÉ™rlÉ™r' if current_lang == 'az' else 'News' }}</h1>
    <form action="/search" method="GET" class="mb-6 flex gap-2">
        <input type="text" name="q" placeholder="{{ 'XÉ™bÉ™r axtar...' if current_lang == 'az' else 'Search news...' }}" class="flex-1 p-2 rounded bg-gray-800 text-white">
        <button type="submit" class="px-4 py-2 bg-cyan-500 rounded">{{ 'Axtar' if current_lang == 'az' else 'Search' }}</button>
    </form>
    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        {% for news in all_news %}
        <a href="/news/{{ news.id }}" class="block bg-gray-800 rounded-lg p-4 card-glow">
            <h3 class="text-xl font-bold text-cyan-300">{{ get_lang_field(news, 'title') }}</h3>
            <p class="text-gray-400">{{ news.category }} | {{ news.published_at.strftime('%d.%m.%Y') }}</p>
            <p class="text-gray-300">{{ get_lang_field(news, 'content')[:150] }}...</p>
        </a>
        {% endfor %}
    </div>
</div>
{% endblock %}
"""
NEWS_DETAIL_HTML = """
{% extends "base.html" %}
{% block title %}{{ get_lang_field(news, 'title') }} - Mi Digital Verse{% endblock %}
{% block content %}
<div class="max-w-4xl mx-auto px-4 py-8">
    <h1 class="text-3xl font-bold mb-4">{{ get_lang_field(news, 'title') }}</h1>
    <p class="text-gray-400">{{ news.category }} | {{ news.published_at.strftime('%d.%m.%Y') }} | {{ 'Oxunma' if current_lang == 'az' else 'Views' }}: {{ news.views }}</p>
    {% if news.image_url %}
    <img src="{{ news.image_url }}" alt="{{ get_lang_field(news, 'title') }}" class="w-full max-h-96 object-contain rounded-lg my-4">
    {% endif %}
    <p class="text-lg leading-relaxed" style="white-space: pre-line;">{{ get_lang_field(news, 'content') }}</p>

    {% for block in news.blocks %}
        {% if block.block_type == 'text' %}
            {% if block.layout == 'side' %}
                <div class="flex flex-col md:flex-row gap-4 my-4">
                    <div class="flex-1"><p class="text-lg" style="white-space: pre-line;">{{ block.text_content_az if current_lang == 'az' else block.text_content_en }}</p></div>
                </div>
            {% else %}
                <p class="text-lg my-4" style="white-space: pre-line;">{{ block.text_content_az if current_lang == 'az' else block.text_content_en }}</p>
            {% endif %}
        {% elif block.block_type == 'image' %}
            {% if block.layout == 'side' %}
                <div class="flex flex-col md:flex-row gap-4 my-4 items-start">
                    <div class="flex-1">
                        {% if block.image_url %}
                            <img src="{{ block.image_url }}" alt="{{ block.title_az if current_lang == 'az' else block.title_en }}" class="w-full max-h-96 object-contain rounded-lg">
                        {% endif %}
                    </div>
                </div>
            {% else %}
                <div class="my-4">
                    {% if block.image_url %}
                        <img src="{{ block.image_url }}" alt="{{ block.title_az if current_lang == 'az' else block.title_en }}" class="w-full max-h-96 object-contain rounded-lg">
                    {% endif %}
                </div>
            {% endif %}
        {% endif %}
    {% endfor %}

    <div class="mt-6 flex gap-3">
        {% if current_user.is_authenticated %}
        <form action="/like-news/{{ news.id }}" method="POST"><button class="px-4 py-2 bg-red-500 rounded">{{ 'BÉ™yÉ™n' if current_lang == 'az' else 'Like' }} ({{ news.likes }})</button></form>
        {% else %}
        <span class="px-4 py-2 bg-gray-700 rounded">{{ 'BÉ™yÉ™nmÉ™' if current_lang == 'az' else 'Likes' }}: {{ news.likes }}</span>
        {% endif %}
        <a href="/create-room?news_id={{ news.id }}" class="px-4 py-2 bg-purple-500 rounded">{{ 'Bu xÉ™bÉ™ri mÃ¼zakirÉ™ et' if current_lang == 'az' else 'Discuss this news' }}</a>
    </div>

    <!-- ÅžÉ™rh bÃ¶lmÉ™si -->
    <div class="mt-8">
        <h2 class="text-2xl font-bold mb-4">{{ 'ÅžÉ™rhlÉ™r' if current_lang == 'az' else 'Comments' }}</h2>

        {% if current_user.is_authenticated %}
        <form action="/news/comment/{{ news.id }}" method="POST" class="mb-6 bg-gray-800 p-4 rounded">
            <textarea name="content" required class="w-full p-2 rounded bg-gray-700 text-white" rows="3" placeholder="{{ 'ÅžÉ™rhinizi yazÄ±n...' if current_lang == 'az' else 'Write your comment...' }}"></textarea>
            <div class="flex items-center mt-2">
                <input type="checkbox" name="is_spoiler" value="1" class="mr-2">
                <span class="text-sm">{{ 'Spoiler olaraq iÅŸarÉ™lÉ™' if current_lang == 'az' else 'Mark as spoiler' }}</span>
            </div>
            <button type="submit" class="mt-2 px-4 py-2 bg-cyan-500 rounded">{{ 'GÃ¶ndÉ™r' if current_lang == 'az' else 'Send' }}</button>
        </form>
        {% else %}
        <p class="mb-4">{{ 'ÅžÉ™rh yazmaq Ã¼Ã§Ã¼n' if current_lang == 'az' else 'To comment' }} <a href="#" onclick="openModal()" class="text-cyan-400">{{ 'giriÅŸ edin' if current_lang == 'az' else 'sign in' }}</a>.</p>
        {% endif %}

        <div class="space-y-4">
            {% for comment in comments %}
            <div class="bg-gray-800 rounded p-3">
                <p class="text-sm text-gray-400">
                    <strong>{{ comment.user.username }}</strong>
                    {% if comment.user.title %}
                        <span style="color: {{ comment.user.title.color }};">({{ comment.user.title.name }})</span>
                    {% endif %}
                    | {{ comment.created_at.strftime('%d.%m.%Y %H:%M') }}
                </p>
                {% if comment.is_spoiler %}
                <span class="spoiler" onclick="this.classList.toggle('revealed')">{{ comment.content }}</span>
                {% else %}
                <p class="text-gray-300 mt-1">{{ comment.content }}</p>
                {% endif %}
                <div class="mt-2 flex gap-2">
                    {% if current_user.is_authenticated %}
                    <button onclick="toggleReplyForm({{ comment.id }})" class="text-xs text-cyan-400">{{ 'Cavabla' if current_lang == 'az' else 'Reply' }}</button>
                    {% endif %}
                    <button onclick="openReportModal('comment', {{ comment.id }})" class="text-xs text-gray-500 hover:text-red-400">{{ 'ÅžikayÉ™t et' if current_lang == 'az' else 'Report' }}</button>
                    {% if current_user.is_authenticated and current_user.is_admin %}
                        <a href="/admin/delete-comment/{{ comment.id }}" class="text-xs text-red-400" onclick="return confirm('{{ 'Bu ÅŸÉ™rhi silmÉ™k istÉ™diyinizÉ™ É™minsiniz?' if current_lang == 'az' else 'Are you sure?' }}')">{{ 'Sil' if current_lang == 'az' else 'Delete' }}</a>
                    {% endif %}
                </div>
                <div id="replyForm{{ comment.id }}" class="hidden mt-3">
                    <form action="/news/comment/{{ news.id }}" method="POST" class="space-y-2">
                        <input type="hidden" name="parent_id" value="{{ comment.id }}">
                        <textarea name="content" required class="w-full p-2 rounded bg-gray-700 text-white" rows="2" placeholder="{{ 'CavabÄ±nÄ±z...' if current_lang == 'az' else 'Your reply...' }}"></textarea>
                        <button type="submit" class="px-3 py-1 bg-cyan-500 rounded">{{ 'GÃ¶ndÉ™r' if current_lang == 'az' else 'Send' }}</button>
                    </form>
                </div>
                {% if comment.replies %}
                <div class="ml-4 mt-2 space-y-2">
                    {% for reply in comment.replies %}
                    <div class="bg-gray-700 rounded p-2">
                        <p class="text-xs text-gray-400">
                            <strong>{{ reply.user.username }}</strong>
                            {% if reply.user.title %}
                                <span style="color: {{ reply.user.title.color }};">({{ reply.user.title.name }})</span>
                            {% endif %}
                            | {{ reply.created_at.strftime('%d.%m.%Y %H:%M') }}
                        </p>
                        {% if reply.is_spoiler %}
                        <span class="spoiler" onclick="this.classList.toggle('revealed')">{{ reply.content }}</span>
                        {% else %}
                        <p class="text-gray-300">{{ reply.content }}</p>
                        {% endif %}
                    </div>
                    {% endfor %}
                </div>
                {% endif %}
            </div>
            {% endfor %}
        </div>
    </div>
</div>

<script>
function toggleReplyForm(commentId) {
    const form = document.getElementById('replyForm' + commentId);
    if (form) {
        form.classList.toggle('hidden');
    }
}
</script>
{% endblock %}
"""

MANGA_LIST_HTML = """
{% extends "base.html" %}
{% block title %}{{ 'Kitabxana' if current_lang == 'az' else 'Library' }} - Mi Digital Verse{% endblock %}
{% block content %}
<div class="max-w-7xl mx-auto px-4 py-8">
    <h1 class="text-3xl font-bold mb-6">{{ 'Manhwa & Anime KitabxanasÄ±' if current_lang == 'az' else 'Manhwa & Anime Library' }}</h1>
    <form action="/manga" method="GET" class="mb-6 flex gap-2">
        <input type="text" name="q" placeholder="{{ 'BaÅŸlÄ±q axtar...' if current_lang == 'az' else 'Search title...' }}" class="flex-1 p-2 rounded bg-gray-800 text-white">
        <select name="type" class="p-2 rounded bg-gray-800 text-white">
            <option value="">{{ 'HamÄ±sÄ±' if current_lang == 'az' else 'All' }}</option>
            <option value="anime">Anime</option>
            <option value="manga">Manga</option>
            <option value="manhwa">Manhwa</option>
            <option value="manhua">Manhua</option>
            <option value="webtoon">Webtoon</option>
        </select>
        <button type="submit" class="px-4 py-2 bg-cyan-500 rounded">{{ 'Axtar' if current_lang == 'az' else 'Search' }}</button>
    </form>
    <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
        {% for m in mangas %}
        <a href="/manga/{{ m.id }}" class="block bg-gray-800 rounded-lg p-3 card-glow">
            <img src="{{ m.cover_url }}" alt="{{ m.title }}" class="w-full h-64 object-cover rounded">
            <h3 class="font-bold mt-2">{{ m.title }}</h3>
            <p class="text-sm text-gray-400">{{ m.type }} | {{ 'Rating:' if current_lang == 'az' else 'Rating:' }} {{ m.rating }}</p>
            <p class="text-xs text-gray-500">{{ m.status }} | {{ m.chapters }} {{ 'bÃ¶lÃ¼m' if current_lang == 'az' else 'chapters' }}</p>
        </a>
        {% endfor %}
    </div>
</div>
{% endblock %}
"""

ARCHIVE_HTML = """
{% extends "base.html" %}
{% block title %}{{ 'Arxiv' if current_lang == 'az' else 'Archive' }} - Mi Digital Verse{% endblock %}
{% block content %}
<div class="max-w-7xl mx-auto px-4 py-8">
    <h1 class="text-3xl font-bold mb-6">{{ 'Arxiv' if current_lang == 'az' else 'Archive' }}</h1>

    <!-- AxtarÄ±ÅŸ vÉ™ FiltrlÉ™r -->
    <form action="/archive" method="GET" class="mb-6 bg-gray-800 p-4 rounded space-y-3">
        <div class="flex flex-col md:flex-row gap-3">
            <input type="text" name="q" value="{{ q }}" placeholder="{{ 'Axtar...' if current_lang == 'az' else 'Search...' }}" class="flex-1 p-2 rounded bg-gray-700 text-white">
            <select name="category" class="p-2 rounded bg-gray-700 text-white">
                <option value="">{{ 'BÃ¼tÃ¼n kateqoriyalar' if current_lang == 'az' else 'All categories' }}</option>
                <option value="anime" {% if category_filter == 'anime' %}selected{% endif %}>Anime</option>
                <option value="manga" {% if category_filter == 'manga' %}selected{% endif %}>Manga</option>
                <option value="manhwa" {% if category_filter == 'manhwa' %}selected{% endif %}>Manhwa</option>
                <option value="manhua" {% if category_filter == 'manhua' %}selected{% endif %}>Manhua</option>
                <option value="webtoon" {% if category_filter == 'webtoon' %}selected{% endif %}>Webtoon</option>
                <option value="oyun" {% if category_filter == 'oyun' %}selected{% endif %}>{{ 'Oyun' if current_lang == 'az' else 'Game' }}</option>
            </select>
            <button type="submit" class="px-4 py-2 bg-cyan-500 rounded">{{ 'Axtar' if current_lang == 'az' else 'Search' }}</button>
        </div>
    </form>

    <!-- NÉ™ticÉ™lÉ™r -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {% if news_results %}
            {% for item in news_results %}
            <a href="/news/{{ item.id }}" class="block bg-gray-800 rounded-lg p-4 card-glow">
                <span class="chip chip-pulse mb-2">{{ item.category }}</span>
                <h3 class="text-xl font-bold text-cyan-300">{{ get_lang_field(item, 'title') }}</h3>
                <p class="text-gray-400 text-sm">{{ get_lang_field(item, 'content')[:100] }}...</p>
                <p class="text-gray-500 text-xs mt-2">{{ item.published_at.strftime('%d.%m.%Y') }} | {{ item.views }} {{ 'oxunma' if current_lang == 'az' else 'views' }}</p>
            </a>
            {% endfor %}
        {% endif %}

        {% if manga_results %}
            {% for m in manga_results %}
            <a href="/manga/{{ m.id }}" class="block bg-gray-800 rounded-lg p-3 card-glow">
                {% if m.cover_url %}
                <img src="{{ m.cover_url }}" alt="{{ m.title }}" class="w-full h-48 object-cover rounded mb-3">
                {% endif %}
                <span class="chip chip-violet">{{ m.type }}</span>
                <h3 class="font-bold mt-2">{{ m.title }}</h3>
                <p class="text-sm text-gray-400">{{ m.description[:80] }}...</p>
                <p class="text-xs text-gray-500 mt-1">{{ 'Rating:' if current_lang == 'az' else 'Rating:' }} {{ m.rating }} | {{ m.status }}</p>
            </a>
            {% endfor %}
        {% endif %}

        {% if not news_results and not manga_results %}
            <p class="col-span-full">{{ 'TapÄ±lmadÄ±.' if current_lang == 'az' else 'Not found.' }}</p>
        {% endif %}
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
    <p class="text-gray-400">{{ manga.type }} | Status: {{ manga.status }} | BÃ¶lÃ¼m: {{ manga.chapters }} | Oxunma: {{ manga.views }}</p>
    {% if manga.cover_url %}
    <img src="{{ manga.cover_url }}" alt="{{ manga.title }}" class="w-full max-h-96 object-contain rounded-lg my-4">
    {% endif %}
    <p class="text-lg leading-relaxed">{{ manga.description }}</p>
    <p class="text-yellow-400 mt-2">Reytinq: {{ manga.rating }}</p>
    <div class="mt-4 flex gap-3">
        {% if current_user.is_authenticated %}
        <form action="/like-manga/{{ manga.id }}" method="POST"><button class="px-4 py-2 bg-red-500 rounded">BÉ™yÉ™n ({{ manga.likes }})</button></form>
        {% else %}
        <span class="px-4 py-2 bg-gray-700 rounded">BÉ™yÉ™nmÉ™: {{ manga.likes }}</span>
        {% endif %}
        <a href="/community" class="inline-block px-4 py-2 bg-purple-500 rounded">Ä°cma mÃ¼zakirÉ™lÉ™ri</a>
    </div>
</div>
{% endblock %}
"""

COMMUNITY_HTML = """
{% extends "base.html" %}
{% block title %}{{ 'Ä°cma' if current_lang == 'az' else 'Community' }} - Mi Digital Verse{% endblock %}
{% block content %}
<div class="max-w-7xl mx-auto px-4 py-8">
    <h1 class="text-3xl font-bold mb-6">{{ 'Ä°cma MÃ¼zakirÉ™lÉ™ri' if current_lang == 'az' else 'Community Discussions' }}</h1>

    <!-- Tabs -->
    <div class="flex flex-wrap gap-2 mb-6">
        <a href="/community?tab=general" class="px-4 py-2 rounded {% if tab == 'general' %}bg-cyan-600 text-white{% else %}bg-gray-700 text-gray-300{% endif %}">
            {{ 'Ãœmumi SÃ¶hbÉ™t' if current_lang == 'az' else 'General Chat' }}
        </a>
        <a href="/community?tab=suggestions" class="px-4 py-2 rounded {% if tab == 'suggestions' %}bg-green-600 text-white{% else %}bg-gray-700 text-gray-300{% endif %}">
            {{ 'TÉ™kliflÉ™r' if current_lang == 'az' else 'Suggestions' }}
        </a>
        <a href="/community?tab=bugs" class="px-4 py-2 rounded {% if tab == 'bugs' %}bg-red-600 text-white{% else %}bg-gray-700 text-gray-300{% endif %}">
            {{ 'XÉ™ta BildiriÅŸi' if current_lang == 'az' else 'Bug Reports' }}
        </a>
    </div>

    <!-- Mesaj yazma formasÄ± -->
    {% if current_user.is_authenticated %}
    <form action="/post/{{ room.id }}" method="POST" class="mb-6 bg-gray-800 p-4 rounded">
        <textarea name="content" placeholder="{{ 'MesajÄ±nÄ±z...' if current_lang == 'az' else 'Your message...' }}" required class="w-full p-2 rounded bg-gray-700 text-white" rows="3"></textarea>
        <div class="flex items-center mt-2">
            <input type="checkbox" name="is_spoiler" value="1" class="mr-2">
            <span class="text-sm">{{ 'Spoiler olaraq iÅŸarÉ™lÉ™' if current_lang == 'az' else 'Mark as spoiler' }}</span>
        </div>
        <button type="submit" class="mt-2 px-4 py-2 bg-cyan-500 rounded">{{ 'GÃ¶ndÉ™r' if current_lang == 'az' else 'Send' }}</button>
    </form>
    {% else %}
    <p class="mb-4">{{ 'Yazmaq Ã¼Ã§Ã¼n' if current_lang == 'az' else 'To write' }} <a href="#" onclick="openModal()" class="text-cyan-400">{{ 'giriÅŸ edin' if current_lang == 'az' else 'sign in' }}</a>.</p>
    {% endif %}

    <!-- Mesajlar -->
    <div class="space-y-4">
        {% for post in posts %}
        <div class="bg-gray-800 rounded p-3">
            <div class="flex items-start justify-between">
                <div>
<p class="text-sm text-gray-400">
    <strong>{{ post.user.username }}</strong>
    {% if post.user.title %}
        <span style="color: {{ post.user.title.color }};">({{ post.user.title.name }})</span>
    {% endif %}
    | {{ post.created_at.strftime('%d.%m.%Y %H:%M') }}
</p>
                    {% if post.is_spoiler %}
                    <span class="spoiler" onclick="this.classList.toggle('revealed')">{{ post.content }}</span>
                    {% else %}
                    <p class="text-gray-300 mt-1">{{ post.content }}</p>
                    {% endif %}
                </div>
                <div class="flex gap-2">
                    {% if current_user.is_authenticated %}
                    <button onclick="openReplyForm({{ post.id }})" class="text-xs text-cyan-400">{{ 'Cavabla' if current_lang == 'az' else 'Reply' }}</button>
                    {% endif %}
                    {% if current_user.is_authenticated and current_user.is_admin %}
                    <a href="/admin/delete-post/{{ post.id }}" class="text-xs text-red-400" onclick="return confirm('{{ 'Bu ÅŸÉ™rhi silmÉ™k istÉ™diyinizÉ™ É™minsiniz?' if current_lang == 'az' else 'Are you sure?' }}')">{{ 'Sil' if current_lang == 'az' else 'Delete' }}</a>
                    {% endif %}
                    <button onclick="openReportModal('post', {{ post.id }})" class="text-xs text-gray-500 hover:text-red-400">{{ 'ÅžikayÉ™t et' if current_lang == 'az' else 'Report' }}</button>
                </div>
            </div>
            <!-- Cavab formasÄ± -->
            <div id="replyForm{{ post.id }}" class="hidden mt-3">
                <form action="/post/{{ room.id }}" method="POST" class="space-y-2">
                    <input type="hidden" name="parent_id" value="{{ post.id }}">
                    <textarea name="content" required class="w-full p-2 rounded bg-gray-700 text-white" rows="2" placeholder="{{ 'CavabÄ±nÄ±z...' if current_lang == 'az' else 'Your reply...' }}"></textarea>
                    <button type="submit" class="px-3 py-1 bg-cyan-500 rounded">{{ 'GÃ¶ndÉ™r' if current_lang == 'az' else 'Send' }}</button>
                </form>
            </div>
            <!-- Cavablar -->
            {% if post.replies %}
            <div class="ml-4 mt-2 space-y-2">
                {% for reply in post.replies %}
                <div class="bg-gray-700 rounded p-2">
                    <p class="text-xs text-gray-400"><strong>{{ reply.user.username }}</strong> | {{ reply.created_at.strftime('%d.%m.%Y %H:%M') }}</p>
                    {% if reply.is_spoiler %}
                    <span class="spoiler" onclick="this.classList.toggle('revealed')">{{ reply.content }}</span>
                    {% else %}
                    <p class="text-gray-300">{{ reply.content }}</p>
                    {% endif %}
                </div>
                {% endfor %}
            </div>
            {% endif %}
        </div>
        {% endfor %}
    </div>
</div>

<script>
function openReplyForm(postId) {
    const form = document.getElementById('replyForm' + postId);
    if (form) {
        form.classList.toggle('hidden');
    }
}
</script>
{% endblock %}
"""

ROOM_HTML = """"
{% extends "base.html" %}
{% block title %}{{ room.name }} - Mi Digital Verse{% endblock %}
{% block content %}
<div class="max-w-4xl mx-auto px-4 py-8">
    <h1 class="text-2xl font-bold mb-4">
        {% if room.name == 'XÉ™ta OtaÄŸÄ±' %}
            {{ 'XÉ™ta OtaÄŸÄ±' if current_lang == 'az' else 'Error Room' }}
        {% else %}
            {{ room.name }}
        {% endif %}
    </h1>
    {% if current_user.is_authenticated %}
    <form action="/post/{{ room.id }}" method="POST" class="mb-6 bg-gray-800 p-4 rounded">
        <textarea name="content" placeholder="{{ 'MesajÄ±nÄ±z...' if current_lang == 'az' else 'Your message...' }}" required class="w-full p-2 rounded bg-gray-700 text-white" rows="3"></textarea>
        <label class="flex items-center mt-2"><input type="checkbox" name="is_spoiler" value="1" class="mr-2"> {{ 'Spoiler olaraq iÅŸarÉ™lÉ™' if current_lang == 'az' else 'Mark as spoiler' }}</label>
        <button type="submit" class="mt-2 px-4 py-2 bg-cyan-500 rounded">{{ 'GÃ¶ndÉ™r' if current_lang == 'az' else 'Send' }}</button>
    </form>
    {% else %}
    <p>{{ 'Yazmaq Ã¼Ã§Ã¼n' if current_lang == 'az' else 'To write' }} <a href="#" onclick="openModal()" class="text-cyan-400">{{ 'giriÅŸ edin' if current_lang == 'az' else 'sign in' }}</a>.</p>
    {% endif %}
    <div class="space-y-4">
        {% for post in posts %}
<div class="bg-gray-800 rounded p-3">
<p class="text-sm text-gray-400">
    <strong>{{ post.user.username }}</strong>
    {% if post.user.title %}
        <span style="color: {{ post.user.title.color }};">({{ post.user.title.name }})</span>
    {% endif %}
    | {{ post.created_at.strftime('%d.%m.%Y %H:%M') }}
</p>
    {% if current_user.is_authenticated and current_user.is_admin %}
        <a href="/admin/delete-post/{{ post.id }}" class="text-red-400 text-xs" onclick="return confirm('{{ 'Bu ÅŸÉ™rhi silmÉ™k istÉ™diyinizÉ™ É™minsiniz?' if current_lang == 'az' else 'Are you sure you want to delete this comment?' }}')">{{ 'ÅžÉ™rhi sil' if current_lang == 'az' else 'Delete comment' }}</a>
    {% endif %}
    <button onclick="openReportModal('post', {{ post.id }})" class="text-xs text-gray-500 hover:text-red-400">{{ 'ÅžikayÉ™t et' if current_lang == 'az' else 'Report' }}</button>
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
{% set achievement_names = {'Ä°lk AddÄ±m': 'First Step', 'XÉ™bÉ™r CanavarÄ±': 'News Beast', 'BÉ™yÉ™nmÉ™ UstasÄ±': 'Like Master', 'ÅžÉ™rh MÃ¼tÉ™xÉ™ssisi': 'Comment Expert', 'Otaq Qurucusu': 'Room Builder', 'GÃ¼ndÉ™lik AsÄ±lÄ±lÄ±q': 'Daily Addiction', 'SÉ™ssiz QÉ™hrÉ™man': 'Silent Hero', 'ÆfsanÉ™vi KolleksiyaÃ§Ä±': 'Legendary Collector'} %}

{% set achievement_descriptions = {'Ä°lk xÉ™bÉ™ri oxu': 'Read first news', '10 xÉ™bÉ™r oxu': 'Read 10 news', '5 bÉ™yÉ™nmÉ™ et': 'Give 5 likes', '5 ÅŸÉ™rh yaz': 'Write 5 comments', '3 mÃ¼zakirÉ™ otaÄŸÄ± yarat': 'Create 3 rooms', '7 gÃ¼n ardÄ±cÄ±l giriÅŸ': '7-day login streak', '50 XP topla': 'Collect 50 XP', '100 XP topla': 'Collect 100 XP'} %}
{% set quest_descriptions = {'1 xÉ™bÉ™r oxu': 'Read 1 news', '1 bÉ™yÉ™nmÉ™ et': 'Like 1 item', '1 ÅŸÉ™rh yaz': 'Write 1 comment', '5 xÉ™bÉ™r oxu': 'Read 5 news', '5 bÉ™yÉ™nmÉ™ et': 'Like 5 items', '1 mÃ¼zakirÉ™ otaÄŸÄ± yarat': 'Create 1 discussion room'} %}
{% set quest_names = {'GÃ¼ndÉ™lik Oxucu': 'Daily Reader', 'GÃ¼ndÉ™lik BÉ™yÉ™nÉ™n': 'Daily Liker', 'GÃ¼ndÉ™lik ÅžÉ™rhÃ§i': 'Daily Commenter', 'HÉ™ftÉ™lik MÉ™hsuldar': 'Weekly Producer', 'HÉ™ftÉ™lik BÉ™yÉ™nÉ™n': 'Weekly Liker', 'HÉ™ftÉ™lik Sosial': 'Weekly Social'} %}
{% extends "base.html" %}
{% block title %}{{ 'Profil' if current_lang == 'az' else 'Profile' }} - Mi Digital Verse{% endblock %}
{% block content %}
<div class="max-w-4xl mx-auto px-4 py-8">
    <h1 class="text-3xl font-bold mb-6">{{ 'Profil' if current_lang == 'az' else 'Profile' }}: {{ current_user.username }}</h1>
    <div class="bg-gray-800 rounded-lg p-6">
        {% if current_user.avatar %}
        <img src="{{ url_for('static', filename='uploads/' + current_user.avatar) }}" alt="Avatar" class="w-24 h-24 rounded-full mb-4">
        {% else %}
        <div class="w-24 h-24 rounded-full bg-gray-600 flex items-center justify-center text-4xl mb-4">{{ current_user.username[0].upper() }}</div>
        {% endif %}
        <p>{{ 'Email' if current_lang == 'az' else 'Email' }}: {{ current_user.email }}</p>
        <p>{{ 'SÉ™viyyÉ™' if current_lang == 'az' else 'Level' }}: {{ current_user.get_level() }}</p>
        <p>{{ 'XP' if current_lang == 'az' else 'XP' }}: {{ current_user.points }} / {{ current_user.get_next_level_xp() }}</p>
        <div class="w-full bg-gray-700 rounded-full h-3 mt-2">
            <div class="bg-cyan-500 h-3 rounded-full" style="width: {{ current_user.get_level_progress() }}%"></div>
        </div>
        <p>{{ 'GÃ¼nlÃ¼k giriÅŸ seriyasÄ±' if current_lang == 'az' else 'Daily login streak' }}: {{ current_user.streak }} {{ 'gÃ¼n' if current_lang == 'az' else 'days' }}</p>
        {% if current_user.title %}
        <p>{{ 'Aktiv Ãœnvan' if current_lang == 'az' else 'Active Title' }}: <span style="color: {{ current_user.title.color }};">{{ current_user.title.name }}</span></p>
        {% endif %}
        {% if not claimed_today %}
        <form action="/claim-daily" method="POST"><button class="px-4 py-2 bg-green-500 rounded mt-2">{{ 'GÃ¼nlÃ¼k Ã¶dÃ¼lÃ¼ al' if current_lang == 'az' else 'Claim daily reward' }}</button></form>
        {% else %}
	<p class="text-green-400 mt-2">{{ 'Bu gÃ¼n Ã¶dÃ¼lÃ¼ almÄ±sÄ±nÄ±z.' if current_lang == 'az' else "You have already claimed today's reward." }}</p>
        {% endif %}
        <h2 class="text-xl font-bold mt-6 mb-3">{{ 'Profil ÅŸÉ™klini dÉ™yiÅŸ' if current_lang == 'az' else 'Change profile picture' }}</h2>
        <form action="/upload-avatar" method="POST" enctype="multipart/form-data" class="space-y-3">
            <input type="file" name="avatar" accept="image/*" required class="w-full p-2 bg-gray-700 rounded">
            <button type="submit" class="px-4 py-2 bg-purple-500 rounded">{{ 'YÃ¼klÉ™' if current_lang == 'az' else 'Upload' }}</button>
        </form>
        <h2 class="text-xl font-bold mt-6 mb-3">{{ 'Bio vÉ™ Sosial KeÃ§idlÉ™r' if current_lang == 'az' else 'Bio and Social Links' }}</h2>
        <form action="/profile/update-bio" method="POST" class="space-y-3">
            <div>
                <label class="text-sm text-gray-400">{{ 'Bio' if current_lang == 'az' else 'Bio' }}</label>
                <textarea name="bio" class="w-full p-2 rounded bg-gray-700 text-white" rows="3">{{ current_user.bio or '' }}</textarea>
            </div>
            <div>
                <label class="text-sm text-gray-400">{{ 'Twitter linki' if current_lang == 'az' else 'Twitter link' }}</label>
                <input type="text" name="twitter_link" value="{{ current_user.twitter_link or '' }}" class="w-full p-2 rounded bg-gray-700 text-white">
            </div>
            <div>
                <label class="text-sm text-gray-400">{{ 'Instagram linki' if current_lang == 'az' else 'Instagram link' }}</label>
                <input type="text" name="instagram_link" value="{{ current_user.instagram_link or '' }}" class="w-full p-2 rounded bg-gray-700 text-white">
            </div>
            <div>
                <label class="text-sm text-gray-400">{{ 'Discord linki' if current_lang == 'az' else 'Discord link' }}</label>
                <input type="text" name="discord_link" value="{{ current_user.discord_link or '' }}" class="w-full p-2 rounded bg-gray-700 text-white">
            </div>
            <button type="submit" class="px-4 py-2 bg-purple-500 rounded">{{ 'Yadda saxla' if current_lang == 'az' else 'Save' }}</button>
        </form>
        <h2 class="text-xl font-bold mt-6 mb-3">{{ 'ÅžifrÉ™ni dÉ™yiÅŸ' if current_lang == 'az' else 'Change password' }}</h2>
        <form action="/profile/change-password" method="POST" class="space-y-3">
            <input type="password" name="current_password" placeholder="{{ 'HazÄ±rkÄ± ÅŸifrÉ™' if current_lang == 'az' else 'Current password' }}" required class="w-full p-2 rounded bg-gray-700 text-white">
            <input type="password" name="new_password" placeholder="{{ 'Yeni ÅŸifrÉ™ (É™n az 8 simvol)' if current_lang == 'az' else 'New password (at least 8 characters)' }}" required class="w-full p-2 rounded bg-gray-700 text-white">
            <input type="password" name="confirm_password" placeholder="{{ 'Yeni ÅŸifrÉ™ni tÉ™krar yaz' if current_lang == 'az' else 'Repeat new password' }}" required class="w-full p-2 rounded bg-gray-700 text-white">
            <button type="submit" class="px-4 py-2 bg-cyan-500 rounded">{{ 'ÅžifrÉ™ni yenilÉ™' if current_lang == 'az' else 'Update password' }}</button>
        </form>
    </div>

    <!-- Ãœnvanlar bÃ¶lmÉ™si -->
    <div class="bg-gray-800 rounded-lg p-6 mt-6">
        <h2 class="text-xl font-bold mb-4">{{ 'QazandÄ±ÄŸÄ±n Ãœnvanlar' if current_lang == 'az' else 'Earned Titles' }}</h2>
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

    <!-- Vitrin bÃ¶lmÉ™si -->
    <div class="bg-gray-800 rounded-lg p-6 mt-6">
        <h2 class="text-xl font-bold mb-4">{{ 'Vitrin (3 seÃ§im)' if current_lang == 'az' else 'Showcase (3 choices)' }}</h2>
        <form action="/profile/set-showcase" method="POST" class="space-y-3">
            <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
                {% for i in range(1, 4) %}
                <div>
                    <label class="text-sm">{{ 'Vitrin' if current_lang == 'az' else 'Showcase' }} {{ i }}</label>
                    <select name="showcase{{ i }}" class="w-full p-2 rounded bg-gray-700 text-white">
                        <option value="">{{ 'BoÅŸ' if current_lang == 'az' else 'Empty' }}</option>
                        {% for ut in earned_titles %}
                        <option value="{{ ut.title.id }}" {% if (i==1 and current_user.showcase1_id == ut.title.id) or (i==2 and current_user.showcase2_id == ut.title.id) or (i==3 and current_user.showcase3_id == ut.title.id) %}selected{% endif %}>{{ ut.title.name }}</option>
                        {% endfor %}
                    </select>
                </div>
                {% endfor %}
            </div>
            <button type="submit" class="px-4 py-2 bg-purple-500 rounded mt-3">{{ 'Vitrinini yadda saxla' if current_lang == 'az' else 'Save showcase' }}</button>
        </form>
    </div>

    <!-- GÃ¶rÉ™vlÉ™r vÉ™ NailiyyÉ™tlÉ™r -->
    <div class="bg-gray-800 rounded-lg p-6 mt-6">
        <h2 class="text-xl font-bold mb-3">{{ 'GÃ¶rÉ™vlÉ™r' if current_lang == 'az' else 'Quests' }}</h2>
        <div class="space-y-2">
            {% for quest in daily_quests %}
            <div class="bg-gray-700 p-3 rounded">
                <div class="flex justify-between">
                    <span>{{ quest_names.get(quest.name, quest.name) if current_lang == 'en' else quest.name }}</span>
                    <span class="text-cyan-400">{{ quest.reward_xp }} XP</span>
                </div>
                <p class="text-sm text-gray-400">{{ quest_descriptions.get(quest.description, quest.description) if current_lang == 'en' else quest.description }}</p>
                {% set progress = user_quests.get(quest.id) %}
                {% if progress and progress.completed %}
                <span class="text-green-400">TamamlandÄ± âœ”</span>
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
                    <span>{{ quest_names.get(quest.name, quest.name) if current_lang == 'en' else quest.name }}</span>
                    <span class="text-cyan-400">{{ quest.reward_xp }} XP</span>
                </div>
                <p class="text-sm text-gray-400">{{ quest_descriptions.get(quest.description, quest.description) if current_lang == 'en' else quest.description }}</p>
                {% set progress = user_quests.get(quest.id) %}
                {% if progress and progress.completed %}
                <span class="text-green-400">TamamlandÄ± âœ”</span>
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
        <h2 class="text-xl font-bold mb-3">{{ 'NailiyyÉ™tlÉ™r' if current_lang == 'az' else 'Achievements' }}</h2>
        <div class="space-y-2">
            {% for ach in all_achievements %}
            <div class="bg-gray-700 p-3 rounded flex items-center gap-3 {% if ach.hidden and not earned_achievements[ach.id] %}opacity-50{% endif %}">
                <div class="text-2xl">{{ ach.badge_icon }}</div>
                <div>
                    <span class="font-bold">{{ achievement_names.get(ach.name, ach.name) if current_lang == 'en' else ach.name }}</span>
                    <p class="text-sm text-gray-400">{{ achievement_descriptions.get(ach.description, ach.description) if current_lang == 'en' else ach.description }}</p>
                    {% if earned_achievements[ach.id] %}
                    <span class="text-green-400">{{ 'QazanÄ±lÄ±b' if current_lang == 'az' else 'Earned' }} âœ”</span>
                    {% else %}
                    <span class="text-gray-500">{{ 'HÉ™lÉ™ qazanÄ±lmayÄ±b' if current_lang == 'az' else 'Not earned yet' }}</span>
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
        <p>SÉ™viyyÉ™: {{ profile_user.get_level() }}</p>
        <p>XP: {{ profile_user.points }}</p>
        {% if profile_user.title %}
        <p>Ãœnvan: <span style="color: {{ profile_user.title.color }};">{{ profile_user.title.name }}</span></p>
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
            {% if profile_user.is_banned %}<span class="text-red-400">BanlÄ±</span>{% else %}<span class="text-green-400">Aktiv</span>{% endif %}
            {% if profile_user.is_muted %}<span class="text-yellow-400"> | Susdurulub</span>{% endif %}
        </p>
    </div>

    {% if current_user.is_admin and profile_user.id != current_user.id %}
    <div class="bg-gray-800 rounded-lg p-6 mt-6">
        <h2 class="text-xl font-bold mb-3">Moderasiya</h2>
        <p class="text-sm text-gray-400 mb-2">Ban mÃ¼ddÉ™tlÉ™ri:</p>
        <div class="flex flex-wrap gap-2">
            <a href="/admin/ban-user/{{ profile_user.id }}?duration=1" class="px-3 py-1 bg-red-500 text-white rounded">1 gÃ¼n</a>
            <a href="/admin/ban-user/{{ profile_user.id }}?duration=7" class="px-3 py-1 bg-red-500 text-white rounded">7 gÃ¼n</a>
            <a href="/admin/ban-user/{{ profile_user.id }}?duration=30" class="px-3 py-1 bg-red-500 text-white rounded">30 gÃ¼n</a>
            <a href="/admin/ban-user/{{ profile_user.id }}?duration=90" class="px-3 py-1 bg-red-500 text-white rounded">3 ay</a>
            <a href="/admin/ban-user/{{ profile_user.id }}?duration=180" class="px-3 py-1 bg-red-500 text-white rounded">6 ay</a>
            <a href="/admin/ban-user/{{ profile_user.id }}?duration=365" class="px-3 py-1 bg-red-500 text-white rounded">12 ay</a>
            <a href="/admin/ban-user/{{ profile_user.id }}?duration=forever" class="px-3 py-1 bg-red-700 text-white rounded">Ã–mÃ¼rlÃ¼k</a>
            {% if profile_user.is_banned %}<a href="/admin/unban-user/{{ profile_user.id }}" class="px-3 py-1 bg-green-500 text-white rounded">BanÄ± aÃ§</a>{% endif %}
        </div>
        <p class="text-sm text-gray-400 mt-4 mb-2">Susdurma mÃ¼ddÉ™tlÉ™ri:</p>
        <div class="flex flex-wrap gap-2">
            <a href="/admin/mute-user/{{ profile_user.id }}?duration=1" class="px-3 py-1 bg-yellow-500 text-white rounded">1 gÃ¼n</a>
            <a href="/admin/mute-user/{{ profile_user.id }}?duration=7" class="px-3 py-1 bg-yellow-500 text-white rounded">7 gÃ¼n</a>
            <a href="/admin/mute-user/{{ profile_user.id }}?duration=30" class="px-3 py-1 bg-yellow-500 text-white rounded">30 gÃ¼n</a>
            {% if profile_user.is_muted %}<a href="/admin/unmute-user/{{ profile_user.id }}" class="px-3 py-1 bg-green-500 text-white rounded">SusturmanÄ± aÃ§</a>{% endif %}
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
    <h1 class="text-3xl font-bold mb-6">{{ 'Admin Panel' if current_lang == 'az' else 'Admin Panel' }}</h1>
    
    <div class="mb-6 bg-gray-800 p-4 rounded">
        <h2 class="text-xl font-bold mb-3">{{ 'SiyahÄ± MÉ™qalÉ™si Yarat' if current_lang == 'az' else 'Create List Article' }}</h2>
        <form action="/admin/generate-listicle" method="POST" class="space-y-3">
            <input type="text" name="topic" placeholder="{{ 'MÉ™sÉ™lÉ™n:' if current_lang == 'az' else 'Example:' }} best 10 isekai anime 2026" required class="w-full p-2 rounded bg-gray-700 text-white">
            <button type="submit" class="px-4 py-2 bg-purple-500 hover:bg-purple-600 text-white rounded">{{ 'SiyahÄ± yarat' if current_lang == 'az' else 'Create list' }}</button>
        </form>
    </div>
    
    <div class="mb-6">
        <a href="/admin/fetch-news" class="px-4 py-2 bg-green-500 hover:bg-green-600 text-white rounded">{{ 'Son xÉ™bÉ™rlÉ™ri avtomatik Ã§É™k' if current_lang == 'az' else 'Auto-fetch latest news' }}</a>
    </div>
    
    <div class="grid grid-cols-1 md:grid-cols-2 gap-8">
        <div class="bg-gray-800 p-4 rounded">
            <h2 class="text-xl font-bold mb-3">{{ 'Yeni XÉ™bÉ™r ÆlavÉ™ Et' if current_lang == 'az' else 'Add New News' }}</h2>
            <form action="/admin/add-news" method="POST" enctype="multipart/form-data" class="space-y-3">
                <input type="text" name="title_az" placeholder="{{ 'AzÉ™rbaycanca BaÅŸlÄ±q' if current_lang == 'az' else 'Azerbaijani Title' }}" required class="w-full p-2 rounded bg-gray-700 text-white">
                <input type="text" name="title_en" placeholder="{{ 'Ä°ngilis BaÅŸlÄ±q (optional)' if current_lang == 'az' else 'English Title (optional)' }}" class="w-full p-2 rounded bg-gray-700 text-white">
                <textarea name="content_az" placeholder="{{ 'AzÉ™rbaycanca MÉ™zmun' if current_lang == 'az' else 'Azerbaijani Content' }}" required class="w-full p-2 rounded bg-gray-700 text-white" rows="5"></textarea>
                <textarea name="content_en" placeholder="{{ 'Ä°ngilis MÉ™zmun (optional)' if current_lang == 'az' else 'English Content (optional)' }}" class="w-full p-2 rounded bg-gray-700 text-white" rows="5"></textarea>
                <input type="text" name="category" placeholder="{{ 'Kateqoriya' if current_lang == 'az' else 'Category' }} (Anime, Manga, Webtoon, {{ 'Oyun' if current_lang == 'az' else 'Games' }}, {{ 'Ãœmumi' if current_lang == 'az' else 'General' }})" value="Anime" class="w-full p-2 rounded bg-gray-700 text-white">
                <input type="text" name="image_url" placeholder="{{ 'ÅžÉ™kil URL' if current_lang == 'az' else 'Image URL' }}" class="w-full p-2 rounded bg-gray-700 text-white">
                <div id="blocksContainer"></div>
                <button type="button" onclick="addTextBlock()" class="px-4 py-2 bg-cyan-500 rounded mt-2">{{ '+ MÉ™tn Bloku' if current_lang == 'az' else '+ Text Block' }}</button>
                <button type="button" onclick="addImageBlock()" class="px-4 py-2 bg-purple-500 rounded mt-2 ml-2">{{ '+ ÅžÉ™kil Bloku' if current_lang == 'az' else '+ Image Block' }}</button>
                <input type="file" name="image_file" accept="image/*" class="w-full p-2 bg-gray-700 rounded text-white">
                <button type="submit" class="px-4 py-2 bg-cyan-500 rounded">{{ 'ÆlavÉ™ et' if current_lang == 'az' else 'Add' }}</button>
            </form>
        </div>
        
        <div class="bg-gray-800 p-4 rounded">
            <h2 class="text-xl font-bold mb-3">{{ 'Yeni Manqa/Anime ÆlavÉ™ Et' if current_lang == 'az' else 'Add New Manga/Anime' }}</h2>
            <form action="/admin/add-manga" method="POST" enctype="multipart/form-data" class="space-y-3">
                <input type="text" name="title" placeholder="{{ 'AzÉ™rbaycanca BaÅŸlÄ±q' if current_lang == 'az' else 'Azerbaijani Title' }}" required class="w-full p-2 rounded bg-gray-700 text-white">
                <input type="text" name="title_en" placeholder="{{ 'Ä°ngilis BaÅŸlÄ±q (optional)' if current_lang == 'az' else 'English Title (optional)' }}" class="w-full p-2 rounded bg-gray-700 text-white">
                <textarea name="description" placeholder="{{ 'AzÉ™rbaycanca AÃ§Ä±qlama' if current_lang == 'az' else 'Azerbaijani Description' }}" required class="w-full p-2 rounded bg-gray-700 text-white" rows="3"></textarea>
                <textarea name="description_en" placeholder="{{ 'Ä°ngilis AÃ§Ä±qlama (optional)' if current_lang == 'az' else 'English Description (optional)' }}" class="w-full p-2 rounded bg-gray-700 text-white" rows="3"></textarea>
                <select name="type" class="w-full p-2 rounded bg-gray-700 text-white">
                    <option value="anime">Anime</option>
                    <option value="manga">Manga</option>
                    <option value="manhwa">Manhwa</option>
                    <option value="manhua">Manhua</option>
                    <option value="webtoon">Webtoon</option>
                </select>
                <input type="text" name="cover_url" placeholder="{{ 'Ãœz ÅŸÉ™kli URL' if current_lang == 'az' else 'Cover image URL' }}" class="w-full p-2 rounded bg-gray-700 text-white">
                <input type="file" name="cover_file" accept="image/*" class="w-full p-2 bg-gray-700 rounded text-white">
                <input type="number" step="0.1" name="rating" placeholder="{{ 'Reytinq' if current_lang == 'az' else 'Rating' }} (mÉ™s. 8.5)" class="w-full p-2 rounded bg-gray-700 text-white">
                <input type="text" name="status" placeholder="{{ 'Status' if current_lang == 'az' else 'Status' }}" value="{{ 'Davam edir' if current_lang == 'az' else 'Ongoing' }}" class="w-full p-2 rounded bg-gray-700 text-white">
                <input type="number" name="chapters" placeholder="{{ 'BÃ¶lÃ¼m sayÄ±' if current_lang == 'az' else 'Chapter count' }}" value="100" class="w-full p-2 rounded bg-gray-700 text-white">
                <button type="submit" class="px-4 py-2 bg-purple-500 rounded">{{ 'ÆlavÉ™ et' if current_lang == 'az' else 'Add' }}</button>
            </form>
        </div>
    </div>
    
    <h2 class="text-2xl font-bold mt-8 mb-3">{{ 'Qaralamalar' if current_lang == 'az' else 'Drafts' }}</h2>
    <div class="space-y-2">
        {% for draft in draft_news %}
        <div class="bg-gray-800 p-3 rounded flex justify-between items-center">
            <span>{{ draft.title }}</span>
            <div>
                <a href="/admin/publish-news/{{ draft.id }}" class="text-green-400 mr-3">{{ 'YayÄ±mla' if current_lang == 'az' else 'Publish' }}</a>
                <a href="/admin/edit-news/{{ draft.id }}" class="text-cyan-400 mr-3">{{ 'RedaktÉ™ et' if current_lang == 'az' else 'Edit' }}</a>
                <a href="/admin/delete-news/{{ draft.id }}" class="text-red-400">{{ 'Sil' if current_lang == 'az' else 'Delete' }}</a>
            </div>
        </div>
        {% endfor %}
    </div>
    
    <h2 class="text-2xl font-bold mt-8 mb-3">{{ 'MÃ¶vcud XÉ™bÉ™rlÉ™r' if current_lang == 'az' else 'Existing News' }}</h2>
    <div class="space-y-2">
        {% for news in all_news %}
        <div class="bg-gray-800 p-3 rounded flex justify-between items-center">
            <span>{{ news.title }}</span>
            <div>
                <a href="/admin/edit-news/{{ news.id }}" class="text-cyan-400 mr-3">{{ 'RedaktÉ™ et' if current_lang == 'az' else 'Edit' }}</a>
                <a href="/admin/delete-news/{{ news.id }}" class="text-red-400">{{ 'Sil' if current_lang == 'az' else 'Delete' }}</a>
            </div>
        </div>
        {% endfor %}
    </div>
    
    <h2 class="text-2xl font-bold mt-8 mb-3">{{ 'MÃ¶vcud Manqa/Anime' if current_lang == 'az' else 'Existing Manga/Anime' }}</h2>
    <div class="space-y-2">
        {% for m in all_manga %}
        <div class="bg-gray-800 p-3 rounded flex justify-between items-center">
            <span>{{ m.title }} ({{ m.type }})</span>
            <div>
                <a href="/admin/edit-manga/{{ m.id }}" class="text-cyan-400 mr-3">{{ 'RedaktÉ™ et' if current_lang == 'az' else 'Edit' }}</a>
                <a href="/admin/delete-manga/{{ m.id }}" class="text-red-400">{{ 'Sil' if current_lang == 'az' else 'Delete' }}</a>
            </div>
        </div>
        {% endfor %}
    </div>
    
    <h2 class="text-2xl font-bold mt-8 mb-3">{{ 'Ä°stifadÉ™Ã§ilÉ™r' if current_lang == 'az' else 'Users' }}</h2>
    <div class="space-y-2">
        {% for user in all_users %}
        <div class="bg-gray-800 p-3 rounded flex justify-between items-center">
            <a href="/user/{{ user.id }}" class="text-cyan-400">{{ user.username }}</a>
            <div>
                {% if user.is_banned %}<span class="text-red-400"> ({{ 'BanlÄ±' if current_lang == 'az' else 'Banned' }})</span>{% endif %}
                {% if user.is_muted %}<span class="text-yellow-400"> ({{ 'Susturulub' if current_lang == 'az' else 'Muted' }})</span>{% endif %}
            </div>
        </div>
        {% endfor %}
    </div>
    
    <h2 class="text-2xl font-bold mt-8 mb-3">{{ 'ÅžikayÉ™tlÉ™r' if current_lang == 'az' else 'Reports' }}</h2>
    <div class="space-y-2">
        {% for item in report_details %}
        <div class="bg-gray-800 p-3 rounded">
            <div class="flex justify-between items-start">
                <div>
                    <p><strong>{{ item.report.reporter.username }}</strong> {{ 'tÉ™rÉ™findÉ™n ÅŸikayÉ™t' if current_lang == 'az' else 'reported' }}</p>
                    <p class="text-sm text-gray-400">{{ 'NÃ¶v' if current_lang == 'az' else 'Type' }}: {{ item.report.target_type }} #{{ item.report.target_id }}</p>
                    <p class="text-sm text-gray-400">{{ 'SÉ™bÉ™b' if current_lang == 'az' else 'Reason' }}: {{ item.report.reason }}</p>
                    <p class="text-xs text-gray-500 mt-2">{{ 'MÉ™zmun' if current_lang == 'az' else 'Content' }}: {{ item.snippet }}</p>
                    <a href="{{ item.link }}" class="text-blue-400 text-xs" target="_blank">{{ 'MÉ™zmuna bax' if current_lang == 'az' else 'View content' }}</a>
                </div>
                <div class="flex gap-2">
                    <a href="/admin/handle-report/{{ item.report.id }}" class="text-green-400">{{ 'HÉ™ll et' if current_lang == 'az' else 'Resolve' }}</a>
                    <a href="/admin/delete-report/{{ item.report.id }}" class="text-red-400">{{ 'Sil' if current_lang == 'az' else 'Delete' }}</a>
                </div>
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
            <span class="font-bold">{{ 'MÉ™tn Bloku' if current_lang == 'az' else 'Text Block' }}</span>
            <button type="button" onclick="this.parentElement.parentElement.remove()" class="text-red-400">{{ 'Sil' if current_lang == 'az' else 'Delete' }}</button>
        </div>
        <input type="hidden" name="block_type" value="text">
        
        <label class="text-xs text-gray-400">{{ 'BaÅŸlÄ±q (AZ)' if current_lang == 'az' else 'Title (AZ)' }}</label>
        <input type="text" name="block_title_az" class="w-full p-2 rounded bg-gray-800 text-white mb-2">
        
        <label class="text-xs text-gray-400">{{ 'MÉ™tn (AZ)' if current_lang == 'az' else 'Text (AZ)' }}</label>
        <textarea name="block_text_az" class="w-full p-2 rounded bg-gray-800 text-white mb-3" rows="4"></textarea>

        <label class="text-xs text-gray-400">{{ 'BaÅŸlÄ±q (EN)' if current_lang == 'az' else 'Title (EN)' }}</label>
        <input type="text" name="block_title_en" class="w-full p-2 rounded bg-gray-800 text-white mb-2">
        
        <label class="text-xs text-gray-400">{{ 'MÉ™tn (EN)' if current_lang == 'az' else 'Text (EN)' }}</label>
        <textarea name="block_text_en" class="w-full p-2 rounded bg-gray-800 text-white mb-2" rows="4"></textarea>

        <select name="block_layout" class="w-full p-2 rounded bg-gray-800 text-white mt-2">
            <option value="stack">{{ 'Alt-alta' if current_lang == 'az' else 'Stacked' }}</option>
            <option value="side">{{ 'Yan-yana' if current_lang == 'az' else 'Side-by-side' }}</option>
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
            <span class="font-bold">{{ 'ÅžÉ™kil Bloku' if current_lang == 'az' else 'Image Block' }}</span>
            <button type="button" onclick="this.parentElement.parentElement.remove()" class="text-red-400">{{ 'Sil' if current_lang == 'az' else 'Delete' }}</button>
        </div>
        <input type="hidden" name="block_type" value="image">
        
        <label class="text-xs text-gray-400">{{ 'BaÅŸlÄ±q (AZ)' if current_lang == 'az' else 'Title (AZ)' }}</label>
        <input type="text" name="block_title_az" class="w-full p-2 rounded bg-gray-800 text-white mb-2">

        <label class="text-xs text-gray-400">{{ 'BaÅŸlÄ±q (EN)' if current_lang == 'az' else 'Title (EN)' }}</label>
        <input type="text" name="block_title_en" class="w-full p-2 rounded bg-gray-800 text-white mb-3">

        <label class="text-xs text-gray-400">{{ 'ÅžÉ™kil URL' if current_lang == 'az' else 'Image URL' }}</label>
        <input type="text" name="block_image_url" class="w-full p-2 rounded bg-gray-800 text-white mb-2">
        
        <label class="text-xs text-gray-400">{{ 'VÉ™ ya fayl yÃ¼klÉ™' if current_lang == 'az' else 'Or upload file' }}</label>
        <input type="file" name="block_image_file" accept="image/*" class="w-full p-2 bg-gray-800 rounded text-white mb-2">

        <select name="block_layout" class="w-full p-2 rounded bg-gray-800 text-white mt-2">
            <option value="stack">{{ 'Alt-alta' if current_lang == 'az' else 'Stacked' }}</option>
            <option value="side">{{ 'Yan-yana' if current_lang == 'az' else 'Side-by-side' }}</option>
        </select>
    `;
    container.appendChild(div);
}
</script>
{% endblock %}
"""

EDIT_NEWS_HTML = """
{% extends "base.html" %}
{% block title %}{{ 'XÉ™bÉ™ri RedaktÉ™ Et' if current_lang == 'az' else 'Edit News' }} - Mi Digital Verse{% endblock %}
{% block content %}
<div class="max-w-4xl mx-auto px-4 py-8">
    <h1 class="text-3xl font-bold mb-6">{{ 'XÉ™bÉ™ri RedaktÉ™ Et' if current_lang == 'az' else 'Edit News' }}</h1>
    <form method="POST" enctype="multipart/form-data" class="bg-gray-800 p-4 rounded space-y-3">
        <!-- Dil seÃ§imi (tab) -->
        <div class="flex gap-3 mb-4">
            <button type="button" id="azTab" class="px-4 py-2 rounded bg-cyan-600 text-white" onclick="switchLang('az')">AZ</button>
            <button type="button" id="enTab" class="px-4 py-2 rounded bg-gray-600 text-white" onclick="switchLang('en')">EN</button>
        </div>

        <!-- AZ mÉ™zmun -->
        <div id="azFields">
            <label class="text-sm text-gray-400">{{ 'AzÉ™rbaycanca BaÅŸlÄ±q' if current_lang == 'az' else 'Azerbaijani Title' }}</label>
            <input type="text" name="title_az" value="{{ news.title }}" required class="w-full p-2 rounded bg-gray-700 text-white">
            <label class="text-sm text-gray-400">{{ 'AzÉ™rbaycanca MÉ™zmun' if current_lang == 'az' else 'Azerbaijani Content' }}</label>
            <textarea name="content_az" required class="w-full p-2 rounded bg-gray-700 text-white" rows="8">{{ news.content }}</textarea>
        </div>

        <!-- EN mÉ™zmun -->
        <div id="enFields" class="hidden">
            <label class="text-sm text-gray-400">{{ 'Ä°ngilis BaÅŸlÄ±q' if current_lang == 'az' else 'English Title' }}</label>
            <input type="text" name="title_en" value="{{ news.title_en or '' }}" class="w-full p-2 rounded bg-gray-700 text-white">
            <label class="text-sm text-gray-400">{{ 'Ä°ngilis MÉ™zmun' if current_lang == 'az' else 'English Content' }}</label>
            <textarea name="content_en" class="w-full p-2 rounded bg-gray-700 text-white" rows="8">{{ news.content_en or '' }}</textarea>
        </div>

        <label class="text-sm text-gray-400">{{ 'Kateqoriya' if current_lang == 'az' else 'Category' }}</label>
        <input type="text" name="category" value="{{ news.category }}" class="w-full p-2 rounded bg-gray-700 text-white">

        <label class="text-sm text-gray-400">{{ 'ÅžÉ™kil URL' if current_lang == 'az' else 'Image URL' }}</label>
        <input type="text" name="image_url" value="{{ news.image_url }}" class="w-full p-2 rounded bg-gray-700 text-white">
        <label class="text-sm text-gray-400">{{ 'ÅžÉ™kil faylÄ± yÃ¼klÉ™' if current_lang == 'az' else 'Upload image file' }}</label>
        <input type="file" name="image_file" accept="image/*" class="w-full p-2 bg-gray-700 rounded text-white">

        <!-- Dinamik Bloklar -->
        <h2 class="text-xl font-bold mt-6 mb-3">{{ 'ÆlavÉ™ Bloklar' if current_lang == 'az' else 'Additional Blocks' }}</h2>
        <div id="blocksContainer"></div>
        <button type="button" onclick="addTextBlock()" class="px-4 py-2 bg-cyan-500 rounded mt-2">{{ '+ MÉ™tn Bloku' if current_lang == 'az' else '+ Text Block' }}</button>
        <button type="button" onclick="addImageBlock()" class="px-4 py-2 bg-purple-500 rounded mt-2 ml-2">{{ '+ ÅžÉ™kil Bloku' if current_lang == 'az' else '+ Image Block' }}</button>

        <button type="submit" class="px-4 py-2 bg-green-500 rounded mt-4">{{ 'Yadda saxla' if current_lang == 'az' else 'Save' }}</button>
    </form>
</div>

<script>
let currentEditLang = '{{ current_lang }}'; // serverdÉ™n gÉ™lÉ™n cari dil

function switchLang(lang) {
    currentEditLang = lang;
    // AZ/EN sahÉ™lÉ™rini gÃ¶stÉ™r/gizlÉ™
    document.getElementById('azFields').style.display = lang === 'az' ? 'block' : 'none';
    document.getElementById('enFields').style.display = lang === 'en' ? 'block' : 'none';
    // Tab stillÉ™ri
    document.getElementById('azTab').classList.toggle('bg-cyan-600', lang === 'az');
    document.getElementById('azTab').classList.toggle('bg-gray-600', lang !== 'az');
    document.getElementById('enTab').classList.toggle('bg-cyan-600', lang === 'en');
    document.getElementById('enTab').classList.toggle('bg-gray-600', lang !== 'en');
    // Blok konteynerindÉ™ dilÉ™ uyÄŸun sahÉ™lÉ™ri gÃ¶stÉ™r/gizlÉ™
    document.querySelectorAll('#blocksContainer .block-az').forEach(el => {
        el.style.display = lang === 'az' ? 'block' : 'none';
    });
    document.querySelectorAll('#blocksContainer .block-en').forEach(el => {
        el.style.display = lang === 'en' ? 'block' : 'none';
    });
}

function addTextBlock() {
    const container = document.getElementById('blocksContainer');
    const div = document.createElement('div');
    div.className = 'bg-gray-700 p-3 rounded mt-3';
    div.innerHTML = `
        <div class="flex justify-between items-center mb-2">
            <span class="font-bold">{{ 'MÉ™tn Bloku' if current_lang == 'az' else 'Text Block' }}</span>
            <button type="button" onclick="this.parentElement.parentElement.remove()" class="text-red-400">{{ 'Sil' if current_lang == 'az' else 'Delete' }}</button>
        </div>
        <input type="hidden" name="block_type" value="text">
        <div class="block-az" style="display:${currentEditLang === 'az' ? 'block' : 'none'};">
            <label class="text-xs text-gray-400">BaÅŸlÄ±q (AZ)</label>
            <input type="text" name="block_title_az" class="w-full p-2 rounded bg-gray-800 text-white">
            <label class="text-xs text-gray-400">MÉ™tn (AZ)</label>
            <textarea name="block_text_az" class="w-full p-2 rounded bg-gray-800 text-white" rows="4"></textarea>
        </div>
        <div class="block-en" style="display:${currentEditLang === 'en' ? 'block' : 'none'};">
            <label class="text-xs text-gray-400">Title (EN)</label>
            <input type="text" name="block_title_en" class="w-full p-2 rounded bg-gray-800 text-white">
            <label class="text-xs text-gray-400">Text (EN)</label>
            <textarea name="block_text_en" class="w-full p-2 rounded bg-gray-800 text-white" rows="4"></textarea>
        </div>
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
            <span class="font-bold">{{ 'ÅžÉ™kil Bloku' if current_lang == 'az' else 'Image Block' }}</span>
            <button type="button" onclick="this.parentElement.parentElement.remove()" class="text-red-400">{{ 'Sil' if current_lang == 'az' else 'Delete' }}</button>
        </div>
        <input type="hidden" name="block_type" value="image">
        <div class="block-az" style="display:${currentEditLang === 'az' ? 'block' : 'none'};">
            <label class="text-xs text-gray-400">BaÅŸlÄ±q (AZ)</label>
            <input type="text" name="block_title_az" class="w-full p-2 rounded bg-gray-800 text-white">
        </div>
        <div class="block-en" style="display:${currentEditLang === 'en' ? 'block' : 'none'};">
            <label class="text-xs text-gray-400">Title (EN)</label>
            <input type="text" name="block_title_en" class="w-full p-2 rounded bg-gray-800 text-white">
        </div>
        <label class="text-xs text-gray-400">ÅžÉ™kil URL</label>
        <input type="text" name="block_image_url" class="w-full p-2 rounded bg-gray-800 text-white">
        <label class="text-xs text-gray-400">VÉ™ ya fayl yÃ¼klÉ™</label>
        <input type="file" name="block_image_file" accept="image/*" class="w-full p-2 bg-gray-800 rounded text-white">
        <select name="block_layout" class="w-full p-2 rounded bg-gray-800 text-white mt-2">
            <option value="stack">Alt-alta</option>
            <option value="side">Yan-yana</option>
        </select>
    `;
    container.appendChild(div);
}

// MÃ¶vcud bloklarÄ± yÃ¼klÉ™
window.onload = function() {
    {% for block in news.blocks %}
        {% if block.block_type == 'text' %}
            const textDiv{{ block.id }} = document.createElement('div');
            textDiv{{ block.id }}.className = 'bg-gray-700 p-3 rounded mt-3';
            textDiv{{ block.id }}.innerHTML = `
                <div class="flex justify-between items-center mb-2">
                    <span class="font-bold">MÉ™tn Bloku</span>
                    <button type="button" onclick="this.parentElement.parentElement.remove()" class="text-red-400">{{ 'Sil' if current_lang == 'az' else 'Delete' }}</button>
                </div>
                <input type="hidden" name="block_type" value="text">
                <div class="block-az">
                    <label class="text-xs text-gray-400">BaÅŸlÄ±q (AZ)</label>
                    <input type="text" name="block_title_az" value="{{ block.title_az }}" class="w-full p-2 rounded bg-gray-800 text-white">
                    <label class="text-xs text-gray-400">MÉ™tn (AZ)</label>
                    <textarea name="block_text_az" class="w-full p-2 rounded bg-gray-800 text-white" rows="4">{{ block.text_content_az }}</textarea>
                </div>
                <div class="block-en">
                    <label class="text-xs text-gray-400">Title (EN)</label>
                    <input type="text" name="block_title_en" value="{{ block.title_en }}" class="w-full p-2 rounded bg-gray-800 text-white">
                    <label class="text-xs text-gray-400">Text (EN)</label>
                    <textarea name="block_text_en" class="w-full p-2 rounded bg-gray-800 text-white" rows="4">{{ block.text_content_en }}</textarea>
                </div>
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
                    <span class="font-bold">ÅžÉ™kil Bloku</span>
                    <button type="button" onclick="this.parentElement.parentElement.remove()" class="text-red-400">{{ 'Sil' if current_lang == 'az' else 'Delete' }}</button>
                </div>
                <input type="hidden" name="block_type" value="image">
                <div class="block-az">
                    <label class="text-xs text-gray-400">BaÅŸlÄ±q (AZ)</label>
                    <input type="text" name="block_title_az" value="{{ block.title_az }}" class="w-full p-2 rounded bg-gray-800 text-white">
                </div>
                <div class="block-en">
                    <label class="text-xs text-gray-400">Title (EN)</label>
                    <input type="text" name="block_title_en" value="{{ block.title_en }}" class="w-full p-2 rounded bg-gray-800 text-white">
                </div>
                <label class="text-xs text-gray-400">ÅžÉ™kil URL</label>
                <input type="text" name="block_image_url" value="{{ block.image_url }}" class="w-full p-2 rounded bg-gray-800 text-white">
                <label class="text-xs text-gray-400">VÉ™ ya fayl yÃ¼klÉ™</label>
                <input type="file" name="block_image_file" accept="image/*" class="w-full p-2 bg-gray-800 rounded text-white">
                <select name="block_layout" class="w-full p-2 rounded bg-gray-800 text-white mt-2">
                    <option value="stack" {% if block.layout == 'stack' %}selected{% endif %}>Alt-alta</option>
                    <option value="side" {% if block.layout == 'side' %}selected{% endif %}>Yan-yana</option>
                </select>
            `;
            document.getElementById('blocksContainer').appendChild(imgDiv{{ block.id }});
        {% endif %}
    {% endfor %}
    // Cari dilÉ™ uyÄŸun sahÉ™lÉ™ri gÃ¶stÉ™r
    switchLang(currentEditLang);
};

</script>
{% endblock %}
"""

EDIT_MANGA_HTML = """
{% extends "base.html" %}
{% block title %}ManqanÄ± RedaktÉ™ Et - Mi Digital Verse{% endblock %}
{% block content %}
<div class="max-w-4xl mx-auto px-4 py-8">
    <h1 class="text-3xl font-bold mb-6">ManqanÄ± RedaktÉ™ Et</h1>
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
        <button type="submit" class="px-4 py-2 bg-purple-500 rounded">{{ 'Yadda saxla' if current_lang == 'az' else 'Save' }}</button>
    </form>
</div>
{% endblock %}
"""

ABOUT_HTML = """
{% extends "base.html" %}
{% block title %}{{ 'HaqqÄ±mÄ±zda' if current_lang == 'az' else 'About Us' }} - Mi Digital Verse{% endblock %}
{% block content %}
<div class="max-w-4xl mx-auto px-4 py-8">
    <h1 class="text-3xl font-bold mb-6">{{ 'HaqqÄ±mÄ±zda' if current_lang == 'az' else 'About Us' }}</h1>
    <p class="text-lg leading-relaxed">
        {% if current_lang == 'az' %}
            Mi Digital Verse, anime, manhwa, manhua vÉ™ manga hÉ™vÉ™skarlarÄ± Ã¼Ã§Ã¼n yaradÄ±lmÄ±ÅŸ mÃ¼asir rÉ™qÉ™msal mÉ™kandÄ±r. MÉ™qsÉ™dimiz pÉ™rÉ™stiÅŸkarlara É™n son xÉ™bÉ™rlÉ™ri, keyfiyyÉ™tli analizlÉ™ri vÉ™ interaktiv icma tÉ™crÃ¼bÉ™sini bir araya gÉ™tirmÉ™kdir.
        {% else %}
            Mi Digital Verse is a modern digital space created for anime, manhwa, manhua, and manga enthusiasts. Our goal is to bring fans together with the latest news, quality analysis, and interactive community experience.
        {% endif %}
    </p>
    <p class="text-lg leading-relaxed">
        {% if current_lang == 'az' %}
            Biz inanÄ±rÄ±q ki, hÉ™r bir pÉ™rÉ™stiÅŸkarÄ±n sÉ™si burada eÅŸidilmÉ™lidir. Ona gÃ¶rÉ™ dÉ™ saytÄ±mÄ±zda mÃ¼zakirÉ™ otaqlarÄ±, nailiyyÉ™tlÉ™r vÉ™ Ã¼nvan sistemi qurmuÅŸuq. GÉ™lÉ™cÉ™kdÉ™ daha Ã§ox funksiya vÉ™ mÉ™zmun É™lavÉ™ edÉ™rÉ™k bÃ¶yÃ¼mÉ™yÉ™ davam edÉ™cÉ™yik.
        {% else %}
            We believe that every fan's voice should be heard here. That's why we have built discussion rooms, achievements, and a title system on our site. We will continue to grow by adding more features and content in the future.
        {% endif %}
    </p>
    <p class="text-lg leading-relaxed">
        {% if current_lang == 'az' %}
            Mi Digital Verse ailÉ™sinÉ™ qoÅŸulun vÉ™ rÉ™qÉ™msal dÃ¼nyada Ã¶z yerinizi alÄ±n!
        {% else %}
            Join the Mi Digital Verse family and take your place in the digital world!
        {% endif %}
    </p>
</div>
{% endblock %}
"""

SEARCH_HTML = """
{% extends "base.html" %}
{% block title %}{{ 'AxtarÄ±ÅŸ' if current_lang == 'az' else 'Search' }} - Mi Digital Verse{% endblock %}
{% block content %}
<div class="max-w-7xl mx-auto px-4 py-8">
    <h1 class="text-2xl mb-4">{{ 'AxtarÄ±ÅŸ:' if current_lang == 'az' else 'Search:' }} "{{ q }}"</h1>
    <h2 class="text-xl mb-3">{{ 'XÉ™bÉ™rlÉ™r' if current_lang == 'az' else 'News' }}</h2>
    {% for n in news_results %}
    <div class="bg-gray-800 p-3 rounded mb-2"><a href="/news/{{ n.id }}" class="text-cyan-300">{{ n.title }}</a></div>
    {% else %}<p>{{ 'TapÄ±lmadÄ±.' if current_lang == 'az' else 'Not found.' }}</p>{% endfor %}
    <h2 class="text-xl mb-3 mt-6">{{ 'Manqa/Anime' if current_lang == 'az' else 'Manga/Anime' }}</h2>
    {% for m in manga_results %}
    <div class="bg-gray-800 p-3 rounded mb-2"><a href="/manga/{{ m.id }}" class="text-cyan-300">{{ m.title }} ({{ m.type }})</a></div>
    {% else %}<p>TapÄ±lmadÄ±.</p>{% endfor %}
</div>
{% endblock %}
"""

NOTIFICATIONS_HTML = """
{% extends "base.html" %}
{% block title %}BildiriÅŸlÉ™r - Mi Digital Verse{% endblock %}
{% block content %}
<div class="max-w-4xl mx-auto px-4 py-8">
    <h1 class="text-3xl font-bold mb-6">BildiriÅŸlÉ™r</h1>
    <div class="space-y-2">
        {% for n in notifications %}
        <div class="bg-gray-800 p-3 rounded flex justify-between items-center {% if not n.is_read %}border-l-4 border-cyan-400{% endif %}">
            <p class="text-gray-300">{{ n.message }}</p>
            <div class="text-sm text-gray-400">
                {{ n.created_at.strftime('%d.%m.%Y %H:%M') }}
                {% if not n.is_read %}
                <a href="/notifications/mark-read/{{ n.id }}" class="ml-2 text-cyan-400">OxunmuÅŸ iÅŸarÉ™lÉ™</a>
                {% endif %}
            </div>
        </div>
        {% else %}
        <p>BildiriÅŸ yoxdur.</p>
        {% endfor %}
    </div>
    <a href="/notifications/mark-all-read" class="mt-4 inline-block px-4 py-2 bg-cyan-500 rounded">HamÄ±sÄ±nÄ± oxunmuÅŸ et</a>
</div>
{% endblock %}
"""

QUESTS_HTML = """
{% extends "base.html" %}
{% block title %}GÃ¶rÉ™vlÉ™r - Mi Digital Verse{% endblock %}
{% block content %}
<div class="max-w-4xl mx-auto px-4 py-8">
    <h1 class="text-3xl font-bold mb-6">GÃ¶rÉ™vlÉ™r</h1>
    <h2 class="text-2xl font-semibold mb-3">GÃ¼ndÉ™lik</h2>
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
                <p class="text-green-400">TamamlandÄ± âœ”</p>
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

    <h2 class="text-2xl font-semibold mt-8 mb-3">HÉ™ftÉ™lik</h2>
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
                <p class="text-green-400">TamamlandÄ± âœ”</p>
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
{% block title %}NailiyyÉ™tlÉ™r - Mi Digital Verse{% endblock %}
{% block content %}
<div class="max-w-4xl mx-auto px-4 py-8">
    <h1 class="text-3xl font-bold mb-6">NailiyyÉ™tlÉ™r</h1>
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        {% for ach in all_achievements %}
        <div class="bg-gray-800 p-4 rounded flex items-center gap-3 {% if ach.hidden and not earned_achievements[ach.id] %}opacity-50{% endif %}">
            <div class="text-3xl">{{ ach.badge_icon }}</div>
            <div>
                <p class="font-bold">{{ ach.name }}</p>
                <p class="text-sm text-gray-400">{{ ach.description }}</p>
                {% if earned_achievements[ach.id] %}
                <p class="text-green-400">QazanÄ±lÄ±b âœ”</p>
                {% else %}
                <p class="text-gray-500">HÉ™lÉ™ qazanÄ±lmayÄ±b</p>
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
    'archive.html': ARCHIVE_HTML,
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
def inject_lang():
    def get_lang_field(obj, field_prefix):
        lang = session.get('lang', 'az')
        if lang == 'en':
            value = getattr(obj, f'{field_prefix}_en', '')
            if value:
                return value
        return getattr(obj, field_prefix, '')
    return {'get_lang_field': get_lang_field, 'current_lang': session.get('lang', 'az')}

@app.context_processor
def inject_unread_notifications():
    if current_user.is_authenticated:
        unread = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
        return {'unread_notifications_count': unread}
    return {'unread_notifications_count': 0}

# ---------- ROUTELAR ----------
@app.route('/set-language/<lang>')
def set_language(lang):
    if lang in ['az', 'en']:
        session['lang'] = lang
    return redirect(request.referrer or url_for('index'))

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

@app.route('/archive')
def archive():
    q = request.args.get('q', '').strip()
    category_filter = request.args.get('category', '')

    news_query = News.query.filter_by(status='published')
    manga_query = Manga.query

    if q:
        news_query = news_query.filter(News.title.contains(q) | News.content.contains(q))
        manga_query = manga_query.filter(Manga.title.contains(q) | Manga.description.contains(q))

    if category_filter:
        if category_filter in ['anime', 'manga', 'manhwa', 'manhua', 'webtoon']:
            manga_query = manga_query.filter(Manga.type == category_filter)
            news_query = news_query.filter(News.category.ilike(f'%{category_filter}%'))
        elif category_filter == 'oyun':
            news_query = news_query.filter(News.category.ilike('%oyun%'))
            manga_query = manga_query.filter(Manga.id == -1)  # oyun manqasÄ± yoxdur
        else:
            news_query = news_query.filter(News.category.ilike(f'%{category_filter}%'))

    news_results = news_query.order_by(News.published_at.desc()).all()
    manga_results = manga_query.order_by(Manga.rating.desc()).all()

    return render_template('archive.html',
                           q=q,
                           category_filter=category_filter,
                           news_results=news_results,
                           manga_results=manga_results)


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
    comments = Comment.query.filter_by(news_id=news.id).order_by(Comment.created_at.asc()).all()
    return render_template('news_detail.html', news=news, comments=comments)

@app.route('/admin/delete-comment/<int:comment_id>')
@login_required
@admin_required
def delete_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    news_id = comment.news_id
    db.session.delete(comment)
    db.session.commit()
    flash(_t('ÅžÉ™rh silindi.', 'Comment deleted.'))
    return redirect(url_for('news_detail', news_id=news_id))

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
    add_notification(current_user, f"Siz {manga.title} É™sÉ™rini bÉ™yÉ™ndiniz.")
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
    tab = request.args.get('tab', 'general')
    if tab == 'suggestions':
        room = Room.query.filter_by(name='TÉ™kliflÉ™r').first()
    elif tab == 'bugs':
        room = Room.query.filter_by(name='XÉ™ta BildiriÅŸi').first()
    else:
        room = Room.query.filter_by(name='Ãœmumi SÃ¶hbÉ™t').first()
        tab = 'general'
    if not room:
        room = Room.query.first()  # fallback
    posts = []
    if room:
        posts = Post.query.filter_by(room_id=room.id).order_by(Post.created_at.asc()).all()
    return render_template('community.html', room=room, posts=posts, tab=tab)

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
            <h1 class="text-3xl font-bold mb-6">Yeni MÃ¼zakirÉ™ OtaÄŸÄ±</h1>
            <form method="POST" class="bg-gray-800 p-4 rounded space-y-3">
                <input type="text" name="room_name" placeholder="Otaq adÄ±" required class="w-full p-2 rounded bg-gray-700 text-white">
                <select name="news_id" class="w-full p-2 rounded bg-gray-700 text-white">
                    <option value="">XÉ™bÉ™r seÃ§ (istÉ™yÉ™ baÄŸlÄ±)</option>
                    {% for n in all_news %}
                    <option value="{{ n.id }}" {% if n.id == selected_news_id %}selected{% endif %}>{{ n.title }}</option>
                    {% endfor %}
                </select>
                <button type="submit" class="px-4 py-2 bg-cyan-500 rounded">OtaÄŸÄ± yarat</button>
            </form>
        </div>
        {% endblock %}
        ''', all_news=all_news, selected_news_id=int(selected_news_id) if selected_news_id else None)
    else:
        name = request.form.get('room_name', '').strip()
        news_id = request.form.get('news_id', '')
        if not name:
            flash(_t('Otaq adÄ± boÅŸ ola bilmÉ™z', 'Room name cannot be empty'))
            return redirect(url_for('community'))
        room = Room(name=name, news_id=int(news_id) if news_id else None, creator_id=current_user.id)
        db.session.add(room)
        db.session.commit()
        update_quest_progress(current_user, 'room_create', 1)
        check_achievements(current_user)
        # BildiriÅŸ: yalnÄ±z xÉ™bÉ™r sahibinÉ™ (É™gÉ™r xÉ™bÉ™rÉ™ baÄŸlÄ±dÄ±rsa)
        if room.news_id:
            news = News.query.get(room.news_id)
            if news and news.author_id and news.author_id != current_user.id:
                author = User.query.get(news.author_id)
                if author:
                    add_notification(author, f"{current_user.username} '{news.title}' xÉ™bÉ™ri Ã¼Ã§Ã¼n mÃ¼zakirÉ™ otaÄŸÄ± yaratdÄ±.")
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
    parent_id = request.form.get('parent_id')
    if parent_id:
        parent_id = int(parent_id)
    else:
        parent_id = None
    if not content:
        return redirect(request.referrer or url_for('community'))
    post = Post(room_id=room_id, user_id=current_user.id, content=content, is_spoiler=is_spoiler, parent_id=parent_id)
    db.session.add(post)
    db.session.commit()
    add_xp(current_user, 5)
    update_quest_progress(current_user, 'post', 1)
    check_achievements(current_user)

    if post.room.name == 'XÉ™ta BildiriÅŸi':
        admin = User.query.filter_by(is_admin=True).first()
        if admin:
            add_notification(admin, f"XÉ™ta BildiriÅŸindÉ™ yeni mesaj: {current_user.username} tÉ™rÉ™findÉ™n.")

    return redirect(request.referrer or url_for('community'))

@app.route('/report/submit', methods=['POST'])
@login_required
def report_submit():
    target_type = request.form.get('target_type')
    target_id = int(request.form.get('target_id'))
    reason = request.form.get('reason', '')

    if reason == 'digÉ™r':
        other_reason = request.form.get('other_reason', '').strip()
        if other_reason:
            reason = other_reason

    if target_type not in ['post', 'room']:
        flash(_t('SÉ™hv ÅŸikayÉ™t nÃ¶vÃ¼.', 'Invalid report type.'))
        return redirect(request.referrer or url_for('index'))

    report = Report(reporter_id=current_user.id, target_type=target_type, target_id=target_id, reason=reason)
    db.session.add(report)
    db.session.commit()
    flash(_t('ÅžikayÉ™t gÃ¶ndÉ™rildi.', 'Report submitted.'))
    return redirect(request.referrer or url_for('index'))

@app.route('/report/post/<int:post_id>', methods=['POST'])
@login_required
def report_post(post_id):
    post = Post.query.get_or_404(post_id)
    reason = request.form.get('reason', '')
    report = Report(reporter_id=current_user.id, target_type='post', target_id=post.id, reason=reason)
    db.session.add(report)
    db.session.commit()
    flash(_t('ÅžikayÉ™t gÃ¶ndÉ™rildi.', 'Report submitted.'))
    return redirect(request.referrer or url_for('index'))

@app.route('/report/room/<int:room_id>', methods=['POST'])
@login_required
def report_room(room_id):
    room = Room.query.get_or_404(room_id)
    reason = request.form.get('reason', '')
    report = Report(reporter_id=current_user.id, target_type='room', target_id=room.id, reason=reason)
    db.session.add(report)
    db.session.commit()
    flash(_t('ÅžikayÉ™t gÃ¶ndÉ™rildi.', 'Report submitted.'))
    return redirect(request.referrer or url_for('index'))

@app.route('/news/comment/<int:news_id>', methods=['POST'])
@login_required
def add_comment(news_id):
    news = News.query.get_or_404(news_id)
    content = request.form.get('content', '').strip()
    parent_id = request.form.get('parent_id')
    is_spoiler = request.form.get('is_spoiler') == '1'
    if not content:
        return redirect(url_for('news_detail', news_id=news.id))
    parent = None
    if parent_id:
        parent = Comment.query.get(int(parent_id))
    comment = Comment(
        news_id=news.id,
        user_id=current_user.id,
        content=content,
        parent_id=parent.id if parent else None,
        is_spoiler=is_spoiler
    )
    db.session.add(comment)
    db.session.commit()
    add_xp(current_user, 5)
    check_achievements(current_user)
    return redirect(url_for('news_detail', news_id=news.id))

@app.route('/like-news/<int:news_id>', methods=['POST'])
@login_required
def like_news(news_id):
    news = News.query.get_or_404(news_id)
    existing_like = NewsLike.query.filter_by(user_id=current_user.id, news_id=news.id).first()
    if existing_like:
        # BÉ™yÉ™nmÉ™ni geri al
        db.session.delete(existing_like)
        news.likes = max(0, news.likes - 1)
        db.session.commit()
        flash(_t('BÉ™yÉ™nmÉ™ geri alÄ±ndÄ±.', 'Like removed.'))
    else:
        # Yeni bÉ™yÉ™nmÉ™
        like = NewsLike(user_id=current_user.id, news_id=news.id)
        db.session.add(like)
        news.likes += 1
        db.session.commit()
        # XP vÉ™ gÃ¶rÉ™vlÉ™r
        add_xp(current_user, 1)
        update_quest_progress(current_user, 'like', 1)
        check_achievements(current_user)
        # BildiriÅŸ: yalnÄ±z xÉ™bÉ™r sahibinÉ™ (É™gÉ™r admin deyilsÉ™ vÉ™ xÉ™bÉ™rin mÃ¼É™llifi varsa)
        if news.author_id and news.author_id != current_user.id:
            author = User.query.get(news.author_id)
            if author:
                add_notification(author, f"{current_user.username} sizin '{news.title}' xÉ™bÉ™rinizi bÉ™yÉ™ndi.")
        else:
            # Ã–z xÉ™bÉ™rini bÉ™yÉ™nÉ™ndÉ™ bildiriÅŸ getmÉ™sin
            pass
    return redirect(url_for('news_detail', news_id=news.id))

# ---------- AUTH ----------
@app.route('/user/<int:user_id>')
@login_required
@admin_required
def user_profile(user_id):
    user = User.query.get_or_404(user_id)
    return render_template('user_profile.html', profile_user=user)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        if not username or not password:
            flash(_t('Ä°stifadÉ™Ã§i adÄ± vÉ™ ÅŸifrÉ™ mÉ™cburidir', 'Username and password are required'))
            return redirect(url_for('register'))
        if not is_strong_password(password):
            flash(_t('ÅžifrÉ™ É™n az 8 simvol, hÉ™rf vÉ™ rÉ™qÉ™m olmalÄ±dÄ±r', 'Password must be at least 8 characters long and contain letters and numbers'))
            return redirect(url_for('register'))
        if email and not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email):
            flash(_t('Email formatÄ± dÃ¼zgÃ¼n deyil', 'Invalid email format'))
            return redirect(url_for('register'))
        if User.query.filter_by(username=username).first():
            flash(_t('Bu istifadÉ™Ã§i adÄ± artÄ±q mÃ¶vcuddur', 'This username already exists'))
            return redirect(url_for('register'))
        if email and User.query.filter_by(email=email).first():
            flash(_t('Bu email artÄ±q qeydiyyatdan keÃ§ib', 'This email is already registered'))
            return redirect(url_for('register'))
        user = User(username=username, email=email, password_hash=generate_password_hash(password))
        db.session.add(user)
        db.session.commit()
        login_user(user)
        start_title = Title.query.filter_by(name="BaÅŸlanÄŸÄ±c").first()
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
        <h1>{{ 'Qeydiyyat' if current_lang == 'az' else 'Register' }}</h1>
        <form method="POST">
            <input type="text" name="username" placeholder="Ä°stifadÉ™Ã§i adÄ±" required><br>
            <input type="email" name="email" placeholder="Email" required><br>
            <input type="password" name="password" placeholder="ÅžifrÉ™ (É™n az 8 simvol)" required><br>
            <button type="submit">{{ 'Qeydiyyatdan keÃ§' if current_lang == 'az' else 'Register' }}</button>
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
                flash(_t('HesabÄ±nÄ±z banlandÄ±.', 'Your account has been banned.'))
                return redirect(url_for('index'))
        login_user(user)
        return redirect(url_for('index'))
    flash(_t('Ä°stifadÉ™Ã§i adÄ± vÉ™ ya ÅŸifrÉ™ yanlÄ±ÅŸdÄ±r', 'Invalid username or password'))
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
    flash(_t('Profil yenilÉ™ndi', 'Profile updated'))
    return redirect(url_for('profile'))

@app.route('/profile/change-password', methods=['POST'])
@login_required
def change_password():
    current_password = request.form.get('current_password', '')
    new_password = request.form.get('new_password', '')
    confirm_password = request.form.get('confirm_password', '')
    if not check_password_hash(current_user.password_hash, current_password):
        flash(_t('HazÄ±rkÄ± ÅŸifrÉ™ yanlÄ±ÅŸdÄ±r', 'Current password is incorrect'))
    elif new_password != confirm_password:
        flash(_t('Yeni ÅŸifrÉ™lÉ™r uyÄŸun gÉ™lmir', 'New passwords do not match'))
    elif not is_strong_password(new_password):
        flash(_t('ÅžifrÉ™ É™n az 8 simvol, hÉ™rf vÉ™ rÉ™qÉ™m olmalÄ±dÄ±r', 'Password must be at least 8 characters long and contain letters and and numbers'))
    else:
        current_user.password_hash = generate_password_hash(new_password)
        db.session.commit()
        flash(_t('ÅžifrÉ™ yenilÉ™ndi', 'Password updated'))
    return redirect(url_for('profile'))

@app.route('/profile/set-active-title/<int:title_id>', methods=['POST'])
@login_required
def set_active_title(title_id):
    title = Title.query.get_or_404(title_id)
    if UserTitle.query.filter_by(user_id=current_user.id, title_id=title.id).first():
        current_user.title_id = title.id
        db.session.commit()
        flash(f"Aktiv Ã¼nvan: {title.name}")
    else:
        flash(_t("Bu Ã¼nvana sahib deyilsiniz.", "You do not own this address."))
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
    flash(_t("Vitrin yenilÉ™ndi", "Showcase updated"))
    return redirect(url_for('profile'))

@app.route('/claim-daily', methods=['POST'])
@login_required
def claim_daily():
    if daily_reward(current_user):
        flash(_t('GÃ¼nlÃ¼k Ã¶dÃ¼l alÄ±ndÄ±!', 'Daily reward claimed!'))
    else:
        flash('Bu gÃ¼n artÄ±q Ã¶dÃ¼l almÄ±sÄ±nÄ±z.')
    return redirect(url_for('profile'))

@app.route('/upload-avatar', methods=['POST'])
@login_required
def upload_avatar():
    if 'avatar' not in request.files:
        flash(_t('Fayl seÃ§ilmÉ™yib', 'No file selected'))
        return redirect(url_for('profile'))
    file = request.files['avatar']
    if file.filename == '':
        flash(_t('Fayl seÃ§ilmÉ™yib', 'No file selected'))
        return redirect(url_for('profile'))
    if file:
        ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
        if ext not in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
            flash(_t('YalnÄ±z ÅŸÉ™kil fayllarÄ± yÃ¼klÉ™yÉ™ bilÉ™rsiniz', 'You can only upload image files'))
            return redirect(url_for('profile'))
        filename = f"{current_user.id}_{datetime.utcnow().timestamp()}.{ext}"
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        current_user.avatar = filename
        db.session.commit()
        flash(_t('Profil ÅŸÉ™kli yenilÉ™ndi', 'Profile picture updated'))
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
    flash(_t("BÃ¼tÃ¼n bildiriÅŸlÉ™r oxunmuÅŸ iÅŸarÉ™lÉ™ndi", "All notifications marked as read"))
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
            content_snippet = target.content[:100] if target else 'SilinmiÅŸ'
            link = url_for('room', room_id=target.room_id) if target else '#'
        elif report.target_type == 'room':
            target = Room.query.get(report.target_id)
            content_snippet = target.name if target else 'SilinmiÅŸ'
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
        title = art.get('title', 'XÉ™bÉ™r')
        content = art.get('content', '')
        category = art.get('category', 'Ãœmumi')
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
    flash(_t(f"{count} xÉ™bÉ™r qaralama olaraq É™lavÉ™ edildi.", f"{count} news added as draft."))
    return redirect(url_for('admin'))

@app.route('/admin/generate-listicle', methods=['POST'])
@login_required
@admin_required
def admin_generate_listicle():
    topic = request.form.get('topic', '').strip()
    if not topic:
        flash(_t('MÃ¶vzu daxil edin', 'Please enter a subject'))
        return redirect(url_for('admin'))
    article = generate_listicle(topic)
    if article:
        title = article.get('title', topic)
        content = article.get('content', '')
        category = article.get('category', 'Ãœmumi')
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
        flash(_t('SiyahÄ± mÉ™qalÉ™si qaralama olaraq yaradÄ±ldÄ±.', 'List article created as draft.'))
    else:
        flash(_t('MÉ™qalÉ™ yaradÄ±la bilmÉ™di, agent boÅŸ nÉ™ticÉ™ qaytardÄ±.', 'Article could not be created, agent returned an empty result.'))
    return redirect(url_for('admin'))

@app.route('/admin/add-news', methods=['POST'])
@login_required
@admin_required
def add_news():
    title = request.form.get('title_az', '').strip()
    content = request.form.get('content_az', '').strip()
    title_en = request.form.get('title_en', '').strip()
    content_en = request.form.get('content_en', '').strip()
    category = request.form.get('category', 'Ãœmumi').strip()
    image_url = request.form.get('image_url', '').strip()
    image_file = request.files.get('image_file')

    if image_file and image_file.filename != '':
        filename = process_image(image_file, 800, 500)
        if filename:
            image_url = filename

    if title and content:
        if not image_url:
            image_url = get_image_url(title)

        news = News(
            title=title,
            title_en=title_en,
            content=content,
            content_en=content_en,
            category=category,
            image_url=image_url,
            author_id=current_user.id,
            status='draft'
        )
        db.session.add(news)
        db.session.commit()

        # BloklarÄ± É™lavÉ™ et
        process_blocks(request, news.id)
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
    user.banned_reason = 'Admin tÉ™rÉ™findÉ™n banlandÄ±'
    db.session.commit()
    flash(_t(f"{user.username} banlandÄ±.", f"{user.username} has been banned."))
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
    user.muted_reason = 'Admin tÉ™rÉ™findÉ™n susturuldu'
    db.session.commit()
    flash(_t(f"{user.username} susturuldu.", f"{user.username} has been muted."))
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
    flash(_t(f"{user.username} banÄ± aÃ§Ä±ldÄ±.", f"{user.username}'s ban has been lifted."))
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
    flash(_t(f"{user.username} susturma aÃ§Ä±ldÄ±.", f"{user.username}'s mute has been lifted."))
    return redirect(url_for('admin'))

@app.route('/admin/handle-report/<int:report_id>')
@login_required
@admin_required
def handle_report(report_id):
    report = Report.query.get_or_404(report_id)
    report.handled = True
    db.session.commit()
    flash(_t("ÅžikayÉ™t hÉ™ll edildi.", "Report resolved."))
    return redirect(url_for('admin'))

@app.route('/admin/delete-report/<int:report_id>')
@login_required
@admin_required
def delete_report(report_id):
    report = Report.query.get_or_404(report_id)
    db.session.delete(report)
    db.session.commit()
    flash(_t("ÅžikayÉ™t silindi.", "Report deleted."))
    return redirect(url_for('admin'))

@app.route('/admin/edit-news/<int:news_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_news(news_id):
    news = News.query.get_or_404(news_id)
    if request.method == 'POST':
        # Yeni É™lavÉ™ edilmiÅŸ Ã§oxdilli sahÉ™lÉ™r
        news.title = request.form.get('title_az', '').strip()
        news.content = request.form.get('content_az', '').strip()
        news.title_en = request.form.get('title_en', '').strip()
        news.content_en = request.form.get('content_en', '').strip()
        
        news.category = request.form.get('category', 'Ãœmumi').strip()
        news.image_url = request.form.get('image_url', '').strip()
        
        image_file = request.files.get('image_file')
        if image_file and image_file.filename != '':
            filename = process_image(image_file, 800, 500)
            if filename:
                news.image_url = filename

        # MÃ¶vcud bloklarÄ± sil
        process_blocks(request, news.id)
        db.session.commit()

        # Yeni bloklarÄ± É™lavÉ™ et
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
        flash(_t('XÉ™bÉ™r yenilÉ™ndi', 'News updated'))
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
        flash(_t('Manqa yenilÉ™ndi', 'Manga updated'))
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
    rating_str = request.form.get('rating', '').strip()
    rating = float(rating_str) if rating_str else 8.0
    status = request.form.get('status', 'Davam edir').strip()
    chapters = int(request.form.get('chapters', 100))

    if cover_file and cover_file.filename != '':
        filename = process_image(cover_file, 400, 600)
        if filename:
            cover_url = filename
        else:
            flash(_t('ÅžÉ™kil formatÄ± dÉ™stÉ™klÉ™nmir, URL istifadÉ™ edilÉ™cÉ™k', 'Image format not supported, URL will be used'))

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
    flash(_t('MÉ™qalÉ™ yayÄ±mlandÄ±.', 'Article published.'))
    return redirect(url_for('admin'))

@app.route('/admin/delete-news/<int:news_id>')
@login_required
@admin_required
def delete_news(news_id):
    news = News.query.get_or_404(news_id)
    # Bu xÉ™bÉ™rÉ™ baÄŸlÄ± otaqlarÄ±n news_id-sini NULL et
    Room.query.filter_by(news_id=news.id).update({'news_id': None})
    # XÉ™bÉ™rÉ™ baÄŸlÄ± hesabatlarÄ± sil (varsa)
    Report.query.filter_by(target_type='news', target_id=news.id).delete()
    db.session.delete(news)
    db.session.commit()
    flash(_t('XÉ™bÉ™r silindi.', 'News deleted.'))
    return redirect(url_for('admin'))

@app.route('/admin/delete-post/<int:post_id>')
@login_required
@admin_required
def admin_delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    user = post.user
    if user:
        add_notification(user, f"Sizin '{post.room.name}' otaÄŸÄ±ndakÄ± ÅŸÉ™rhiniz admin tÉ™rÉ™findÉ™n silindi.")
    room_id = post.room_id
    db.session.delete(post)
    db.session.commit()
    flash(_t('ÅžÉ™rh silindi.', 'Comment deleted.'))
    return redirect(request.referrer or url_for('room', room_id=room_id))

@app.route('/admin/clear-room-messages/<int:room_id>')
@login_required
@admin_required
def admin_clear_room_messages(room_id):
    room = Room.query.get_or_404(room_id)
    if room.name == 'XÉ™ta OtaÄŸÄ±':
        Post.query.filter_by(room_id=room.id).delete()
        db.session.commit()
        flash(_t('XÉ™ta OtaÄŸÄ±ndakÄ± bÃ¼tÃ¼n mesajlar silindi.', 'All messages in the Error Room have been deleted.'))
    else:
        flash(_t('Bu É™mÉ™liyyat yalnÄ±z XÉ™ta OtaÄŸÄ± Ã¼Ã§Ã¼n keÃ§É™rlidir.', 'This operation is only valid for the Error Room.'))
    return redirect(request.referrer or url_for('community'))

@app.route('/admin/delete-room/<int:room_id>')
@login_required
@admin_required
def admin_delete_room(room_id):
    room = Room.query.get_or_404(room_id)
    if room.name == 'XÉ™ta OtaÄŸÄ±' or room.name == 'TÉ™kliflÉ™r OtaÄŸÄ±':
        flash(_t('Bu otaq silinÉ™ bilmÉ™z.', 'This room cannot be deleted.'))
        return redirect(request.referrer or url_for('community'))
    creator = room.creator
    if creator:
        add_notification(creator, f"Sizin '{room.name}' otaÄŸÄ±nÄ±z admin tÉ™rÉ™findÉ™n silindi.")
    Post.query.filter_by(room_id=room.id).delete()
    db.session.delete(room)
    db.session.commit()
    flash(_t('Otaq silindi.', 'Room deleted.'))
    return redirect(request.referrer or url_for('community'))

@app.route('/admin/clear-all-posts')
@login_required
@admin_required
def clear_all_posts():
    Post.query.delete()
    db.session.commit()
    flash(_t('BÃ¼tÃ¼n ÅŸÉ™rhlÉ™r silindi.', 'All comments deleted.'))
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
def ensure_columns():
    import sqlite3
    db_path = os.path.join(app.root_path, 'instance', 'site.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # title cÉ™dvÉ™li
    try:
        cursor.execute("ALTER TABLE title ADD COLUMN required_xp INTEGER DEFAULT 0")
    except:
        pass

    # news cÉ™dvÉ™li
    try:
        cursor.execute("ALTER TABLE news ADD COLUMN status VARCHAR(20) DEFAULT 'draft'")
    except:
        pass
    try:
        cursor.execute("ALTER TABLE news ADD COLUMN title_en VARCHAR(200) DEFAULT ''")
    except:
        pass
    try:
        cursor.execute("ALTER TABLE news ADD COLUMN content_en TEXT DEFAULT ''")
    except:
        pass

    # manga cÉ™dvÉ™li
    try:
        cursor.execute("ALTER TABLE manga ADD COLUMN title_en VARCHAR(200) DEFAULT ''")
    except:
        pass
    try:
        cursor.execute("ALTER TABLE manga ADD COLUMN description_en TEXT DEFAULT ''")
    except:
        pass
    try:
        cursor.execute("ALTER TABLE news_block ADD COLUMN title_az VARCHAR(200) DEFAULT ''")
    except:
        pass
    try:
        cursor.execute("ALTER TABLE news_block ADD COLUMN title_en VARCHAR(200) DEFAULT ''")
    except:
        pass

    conn.commit()
    conn.close()

def init_db():
    with app.app_context():
        ensure_columns()
        db.create_all()
        if not User.query.filter_by(is_admin=True).first():
            admin = User(username='Anuun', email='admin@midigitalverse.com', password_hash=generate_password_hash('MiriMID26&'), is_admin=True, points=100)
            db.session.add(admin)
            db.session.commit()
            print("Admin istifadÉ™Ã§i yaradÄ±ldÄ±: admin / MiriMID26&")
        admin = User.query.filter_by(is_admin=True).first()
        admin_title = Title.query.filter_by(name="Admin").first()
        if admin_title:
            admin.title_id = admin_title.id
            db.session.commit()
        if News.query.count() == 0 and Manga.query.count() == 0:
            print("Ä°lkin mÉ™zmun yaradÄ±lÄ±r...")
            news_items = generate_news_content()
            for item in news_items:
                image_url = item.get('image_url', '')
                if not image_url:
                    image_url = get_image_url(item.get('title', ''))
                news = News(title=item.get('title', 'XÉ™bÉ™r'), content=item.get('content', ''), category=item.get('category', 'Ãœmumi'), image_url=image_url)
                db.session.add(news)
            manga_items = generate_manga_content()
            for item in manga_items:
                cover_url = item.get('cover_url', '')
                if not cover_url:
                    cover_url = get_image_url(item.get('title', ''))
                manga = Manga(title=item.get('title', 'Manqa'), description=item.get('description', ''), type=item.get('type', 'anime'), cover_url=cover_url, rating=float(item.get('rating', 8.0)), status=item.get('status', 'Davam edir'), chapters=int(item.get('chapters', 100)))
                db.session.add(manga)
            db.session.commit()
            print("Ä°lkin mÉ™zmun bazaya yazÄ±ldÄ±.")
        seed_titles()
        seed_quests_and_achievements()
        # ÃœÃ§ É™sas otaÄŸÄ± yaradÄ±n vÉ™ kÃ¶hnÉ™ adlarÄ± dÉ™yiÅŸdirin
        room_names = ["Ãœmumi SÃ¶hbÉ™t", "TÉ™kliflÉ™r", "XÉ™ta BildiriÅŸi"]
        for name in room_names:
            room = Room.query.filter_by(name=name).first()
            if not room:
                room = Room(name=name, news_id=None, creator_id=admin.id)
                db.session.add(room)
                db.session.commit()
                print(f"{name} otaÄŸÄ± yaradÄ±ldÄ±.")
        # KÃ¶hnÉ™ adlarÄ± dÉ™yiÅŸÉ™k (É™gÉ™r mÃ¶vcuddursa)
        old_error = Room.query.filter_by(name="XÉ™ta OtaÄŸÄ±").first()
        if old_error:
            old_error.name = "XÉ™ta BildiriÅŸi"
        old_suggestion = Room.query.filter_by(name="TÉ™kliflÉ™r OtaÄŸÄ±").first()
        if old_suggestion:
            old_suggestion.name = "TÉ™kliflÉ™r"
        db.session.commit()

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
