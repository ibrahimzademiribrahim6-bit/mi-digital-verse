import os
import re
import json
import random
import requests
from datetime import datetime, date, timedelta, timezone
from functools import wraps

from flask import Flask, render_template, render_template_string, request, redirect, url_for, flash, abort, jsonify, session
from flask_talisman import Talisman
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from jinja2 import DictLoader
from PIL import Image

from models import db, User, News, Manga, Room, Post, Title, Achievement, UserAchievement, Notification, Quest, UserQuest, Gif
from content_generator import generate_news_content, generate_manga_content, get_image_url

load_dotenv()

app = Flask(__name__)
Talisman(app, content_security_policy=None)
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"]
)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'gizli-acar-12345')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 8 * 1024 * 1024  # 8 MB

db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

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
def daily_reward(user):
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

    # Görəv/nailiyyət yenilə
    update_quest_progress(user, 'daily_login', 1)
    update_quest_progress(user, 'points', bonus)
    check_achievements(user)

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

def add_notification(user, message):
    if not user:
        return
    notif = Notification(user_id=user.id, message=message)
    db.session.add(notif)
    db.session.commit()

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

# ---------- Görəv və Nailiyyət Sistemi ----------
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
            # Gizli nailiyyətlər
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
            # Həftəlik reset üçün həftə başlanğıcını yoxla
            week_start = (date.today() - timedelta(days=date.today().weekday())).isoformat()
            if uq.last_reset_date != week_start:
                uq.progress = 0
                uq.completed = False
                uq.last_reset_date = week_start
    db.session.commit()

def update_quest_progress(user, action_type, amount=1):
    if not user.is_authenticated:
        return
    # Görəvləri sıfırla (gündəlik/həftəlik)
    reset_user_quests(user)

    # Aktiv görəvləri tap
    quests = Quest.query.filter(
        (Quest.is_daily == True) | (Quest.is_weekly == True)
    ).all()

    for quest in quests:
        if quest.requirement_type != action_type:
            continue
        # İstifadəçinin bu görəv üçün qeydini tap və ya yarat
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
            user.points += quest.reward_xp
            add_notification(user, f"Görəvi tamamladın: {quest.name} (+{quest.reward_xp} XP)")
        db.session.commit()

def check_achievements(user):
    if not user.is_authenticated:
        return
    achievements = Achievement.query.all()
    for ach in achievements:
        # Artıq qazanılıbsa keç
        if UserAchievement.query.filter_by(user_id=user.id, achievement_id=ach.id).first():
            continue
        earned = False
        if ach.requirement_type == 'news_read':
            earned = user.news_read_count >= ach.requirement_value
        elif ach.requirement_type == 'like':
            # Bəyənmə sayını təyin et (aşağıda saxlanacaq)
            likes_count = user.likes_count if hasattr(user, 'likes_count') else 0
            earned = likes_count >= ach.requirement_value
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
            # Bəzi nailiyyətlər XP də verə bilər, amma indi vermirik.
    db.session.commit()

# ---------- HTML Şablonları ----------
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
        html.light body { background: #f9fafb; color: #111; }
        html.light .bg-gray-800 { background-color: #ffffff; border: 1px solid #e5e7eb; }
        html.light .bg-gray-700 { background-color: #e5e7eb; color: #111; }
        html.light .bg-gray-900 { background-color: #ffffff; border-color: #e5e7eb; }
        html.light .text-gray-300 { color: #374151; }
        html.light .text-gray-400 { color: #4b5563; }
        html.light .text-cyan-300 { color: #0e7490; }
        html.light .text-cyan-400 { color: #0891b2; }
        html.light .text-purple-400 { color: #9333ea; }
        html.light .text-purple-500 { color: #7e22ce; }
        html.light .text-yellow-400 { color: #ca8a04; }
        html.light input, html.light textarea, html.light select { background-color: #fff; color: #111; border: 1px solid #d1d5db; }
        html.light nav, html.light footer { background-color: #ffffff; border-color: #e5e7eb; }
        .hero-section { background: linear-gradient(135deg, #1a1a2e, #16213e, #0f3460); }
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
                    <button id="themeToggle" class="p-2 rounded-full bg-gray-800 text-yellow-400">🌙</button>
                    <button id="mobileMenuBtn" class="md:hidden p-2 rounded bg-gray-800 text-white">☰</button>
                </div>
            </div>
        </div>
        <div id="mobileMenu" class="hidden md:hidden bg-gray-900 px-4 pb-4">
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
                <input type="email" name="email" placeholder="Email" required class="w-full p-2 rounded bg-gray-700 text-white">
                <input type="password" name="password" placeholder="Şifrə (min 6 simvol)" required class="w-full p-2 rounded bg-gray-700 text-white">
                <button type="submit" class="w-full py-2 bg-purple-500 hover:bg-purple-600 text-white rounded">Qeydiyyatdan keç</button>
            </form>
        </div>
    </div>

    <main class="flex-grow">
        {% block content %}{% endblock %}
    </main>

    <footer class="bg-gray-900 text-gray-400 py-6 border-t border-gray-700">
        <div class="max-w-7xl mx-auto text-center">
            <p>© {{ now.year }} Mi Digital Verse. Bütün hüquqlar qorunur.</p>
        </div>
    </footer>
</div>

<script>
    const html = document.documentElement;
    if (localStorage.getItem('theme') === 'light') {
        html.classList.remove('dark');
        html.classList.add('light');
        document.getElementById('themeToggle').textContent = '☀️';
    }
    document.getElementById('themeToggle').addEventListener('click', () => {
        if (html.classList.contains('dark')) {
            html.classList.remove('dark');
            html.classList.add('light');
            localStorage.setItem('theme', 'light');
            document.getElementById('themeToggle').textContent = '☀️';
        } else {
            html.classList.remove('light');
            html.classList.add('dark');
            localStorage.setItem('theme', 'dark');
            document.getElementById('themeToggle').textContent = '🌙';
        }
    });
    document.getElementById('mobileMenuBtn').addEventListener('click', () => {
        document.getElementById('mobileMenu').classList.toggle('hidden');
    });
    function openModal() { document.getElementById('authModal').classList.remove('hidden'); }
    function closeModal() { document.getElementById('authModal').classList.add('hidden'); }
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
</script>
</body>
</html>
"""

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
    <p class="text-lg leading-relaxed">{{ news.content }}</p>
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
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <!-- Sol tərəf: Normal otaqlar -->
        <div class="lg:col-span-2">
            <h2 class="text-xl font-bold mb-3">Müzakirə Otaqları</h2>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                {% for room in rooms if room.name != 'Xəta Otağı' %}
                <a href="/room/{{ room.id }}" class="block bg-gray-800 rounded-lg p-4 card-glow">
                    <h3 class="font-bold text-cyan-300">{{ room.name }}</h3>
                    <p class="text-sm text-gray-400">Yaradıcı: {{ room.creator.username }}</p>
                    {% if room.news %}<p class="text-xs text-gray-500">Xəbər: {{ room.news.title }}</p>{% endif %}
                </a>
                {% endfor %}
            </div>
        </div>

        <!-- Sağ tərəf: Xəta Otağı -->
        <div>
            <h2 class="text-xl font-bold mb-3 text-red-400">Xəta Otağı</h2>
            {% for room in rooms if room.name == 'Xəta Otağı' %}
            <a href="/room/{{ room.id }}" class="block bg-red-900 bg-opacity-30 border border-red-500 rounded-lg p-4 card-glow">
                <h3 class="font-bold text-red-300">{{ room.name }}</h3>
                <p class="text-sm text-gray-400">Yaradıcı: {{ room.creator.username }}</p>
            </a>
            {% endfor %}
        </div>
    </div>
    </div>
</div>
{% endblock %}
"""

ROOM_HTML = """
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
	<div class="mb-6 bg-gray-800 p-4 rounded">
    <h3 class="text-lg font-bold mb-2">GIF əlavə et</h3>
    <form action="/upload-gif" method="POST" class="flex gap-2">
        <input type="text" name="gif_url" placeholder="GIF URL" required class="flex-1 p-2 rounded bg-gray-700 text-white">
        <button type="submit" class="px-4 py-2 bg-purple-500 rounded">Yüklə</button>
    </form>
    <div class="mt-3 grid grid-cols-3 gap-2">
        {% for gif in recent_gifs %}
        <img src="{{ gif.url }}" class="w-full h-24 object-cover rounded cursor-pointer" onclick="addGifToMessage('{{ gif.url }}')">
        {% endfor %}
    </div>
</div>
    <div class="space-y-4">
        {% for post in posts %}
        <div class="bg-gray-800 rounded p-3">
            <p class="text-sm text-gray-400"><strong>{{ post.user.username }}</strong> | {{ post.created_at.strftime('%d.%m.%Y %H:%M') }}</p>
            {% if post.is_spoiler %}
            <span class="spoiler" onclick="this.classList.toggle('revealed')">{{ post.content }}</span>
            {% else %}
            <p class="text-gray-300">{{ post.content }}</p>
            {% endif %}
        </div>
        {% endfor %}
    </div>
</div>
<script>
function addGifToMessage(url) {
    const textarea = document.querySelector('textarea[name="content"]');
    textarea.value += ' ' + url + ' ';
    textarea.focus();
}
</script>
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
        <p>Ünvan: <span style="color: {{ current_user.title.color }};">{{ current_user.title.name }}</span></p>
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
        <p class="text-sm text-gray-500 mt-4">Gələcəkdə profil çərçivəsi və arxa planı satın ala biləcəksiniz.</p>
<h2 class="text-xl font-bold mt-6 mb-3">Görəvlər</h2>
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

<h2 class="text-xl font-bold mt-6 mb-3">Nailiyyətlər</h2>
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

ADMIN_HTML = """
{% extends "base.html" %}
{% block title %}Admin Panel - Mi Digital Verse{% endblock %}
{% block content %}
<div class="max-w-7xl mx-auto px-4 py-8">
    <h1 class="text-3xl font-bold mb-6">Admin Panel</h1>
    <div class="grid grid-cols-1 md:grid-cols-2 gap-8">
        <div class="bg-gray-800 p-4 rounded">
            <h2 class="text-xl font-bold mb-3">Yeni Xəbər Əlavə Et</h2>
            <form action="/admin/add-news" method="POST" enctype="multipart/form-data" class="space-y-3">
                <input type="text" name="title" placeholder="Başlıq" required class="w-full p-2 rounded bg-gray-700 text-white">
                <textarea name="content" placeholder="Məzmun" required class="w-full p-2 rounded bg-gray-700 text-white" rows="5"></textarea>
                <input type="text" name="category" placeholder="Kateqoriya (Anime, Manga, Webtoon, Oyun, Ümumi)" value="Anime" class="w-full p-2 rounded bg-gray-700 text-white">
                <input type="text" name="image_url" placeholder="Şəkil URL" class="w-full p-2 rounded bg-gray-700 text-white">
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
        <button type="submit" class="px-4 py-2 bg-cyan-500 rounded">Yadda saxla</button>
    </form>
</div>
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
    <p class="text-lg">Mi Digital Verse, anime, manhwa, manhua və manga həvəskarları üçün yaradılmış müasir rəqəmsal məkandır. Biz ən son xəbərləri, dərin analizləri və cəmiyyətin müzakirələrini bir araya gətiririk. Məqsədimiz pərəstişkarlara zəngin məzmun və interaktiv platforma təqdim etməkdir.</p>
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
    <a href="/notifications?mark_all_read=1" class="inline-block mb-4 px-4 py-2 bg-cyan-600 hover:bg-cyan-700 text-white rounded">Hamısını oxunmuş işarələ</a>
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
    'admin.html': ADMIN_HTML,
    'edit_news.html': EDIT_NEWS_HTML,
    'edit_manga.html': EDIT_MANGA_HTML,
    'about.html': ABOUT_HTML,
    'search.html': SEARCH_HTML,
    'notifications.html': NOTIFICATIONS_HTML,
    'quests.html': QUESTS_HTML,
    'achievements.html': ACHIEVEMENTS_HTML,
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
    latest_news = News.query.order_by(News.published_at.desc()).limit(5).all()
    most_read = News.query.order_by(News.views.desc()).limit(5).all()
    featured = Manga.query.order_by(Manga.rating.desc()).limit(4).all()
    return render_template('index.html', latest_news=latest_news, most_read=most_read, featured=featured)

@app.route('/news')
def news_list():
    all_news = News.query.order_by(News.published_at.desc()).all()
    return render_template('news_list.html', all_news=all_news)

@app.route('/news/<int:news_id>')
def news_detail(news_id):
    news = News.query.get_or_404(news_id)
    if can_increment_view(news.id):
        news.views += 1
        db.session.commit()
        if current_user.is_authenticated:
            current_user.news_read_count += 1
            current_user.points += 2
            db.session.commit()
            update_quest_progress(current_user, 'news_read', 1)
            check_achievements(current_user)
    return render_template('news_detail.html', news=news)

@app.route('/category/<string:cat>')
def category(cat):
    all_news = News.query.filter(News.category.ilike(f'%{cat}%')).order_by(News.published_at.desc()).all()
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
    current_user.points += 1
    db.session.commit()
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
        news_results = News.query.filter(News.title.contains(q) | News.content.contains(q)).all()
        manga_results = Manga.query.filter(Manga.title.contains(q) | Manga.description.contains(q)).all()
        if type_filter:
            manga_results = [m for m in manga_results if m.type == type_filter]
    return render_template('search.html', q=q, news_results=news_results, manga_results=manga_results)

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
        add_notification(current_user, f"Siz '{room.name}' adlı müzakirə otağı yaratdınız.")
        return redirect(url_for('community'))

@app.route('/room/<int:room_id>')
def room(room_id):
    room = Room.query.get_or_404(room_id)
    posts = Post.query.filter_by(room_id=room_id).order_by(Post.created_at.asc()).all()
    recent_gifs = Gif.query.order_by(Gif.created_at.desc()).limit(6).all()
    return render_template('room.html', room=room, posts=posts, recent_gifs=recent_gifs)

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
    current_user.points += 5
    db.session.commit()
    update_quest_progress(current_user, 'post', 1)
    check_achievements(current_user)
    add_notification(current_user, f"Siz '{post.room.name}' otağında yeni mesaj yazdınız.")
    return redirect(url_for('room', room_id=room_id))

@app.route('/like-news/<int:news_id>', methods=['POST'])
@login_required
def like_news(news_id):
    news = News.query.get_or_404(news_id)
    news.likes += 1
    db.session.commit()
    current_user.points += 1
    db.session.commit()
    update_quest_progress(current_user, 'like', 1)
    check_achievements(current_user)
    add_notification(current_user, f"Siz '{news.title}' xəbərini bəyəndiniz.")
    return redirect(url_for('news_detail', news_id=news.id))

# ---------- AUTH ----------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        if not username or not email or not password:
            flash('Bütün sahələr doldurulmalıdır')
            return redirect(url_for('register'))
        if not is_strong_password(password):
            flash('Şifrə ən az 8 simvol, hərf və rəqəm olmalıdır')
            return redirect(url_for('register'))
        if not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email):
            flash('Email formatı düzgün deyil')
            return redirect(url_for('register'))
        if User.query.filter_by(username=username).first():
            flash('Bu istifadəçi adı artıq mövcuddur')
            return redirect(url_for('register'))
        if User.query.filter_by(email=email).first():
            flash('Bu email artıq qeydiyyatdan keçib')
            return redirect(url_for('register'))
        user = User(username=username, email=email, password_hash=generate_password_hash(password))
        db.session.add(user)
        db.session.commit()
        login_user(user)
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
            <input type="password" name="password" placeholder="Şifrə" required><br>
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
    # Görəvlər üçün məlumatlar
    reset_user_quests(current_user)
    daily_quests = Quest.query.filter_by(is_daily=True).all()
    weekly_quests = Quest.query.filter_by(is_weekly=True).all()
    user_quests = {}
    for uq in current_user.quests:
        user_quests[uq.quest_id] = uq
    # Nailiyyətlər üçün
    all_achievements = Achievement.query.all()
    earned_ids = [ua.achievement_id for ua in current_user.achievements]
    earned_achievements = {ach.id: (ach.id in earned_ids) for ach in all_achievements}
    return render_template('profile.html', 
                           claimed_today=claimed_today,
                           daily_quests=daily_quests,
                           weekly_quests=weekly_quests,
                           user_quests=user_quests,
                           all_achievements=all_achievements,
                           earned_achievements=earned_achievements)

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
@app.route('/notifications')
@login_required
def notifications():
    # ?mark_all_read=1 parametri varsa hamısını oxunmuş et
    if request.args.get('mark_all_read') == '1':
        Notification.query.filter_by(user_id=current_user.id, is_read=False).update({'is_read': True})
        db.session.commit()
        flash('Bütün bildirişlər oxunmuş işarələndi.')
        return redirect(url_for('notifications'))
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

# ---------- QUESTS & ACHIEVEMENTS ----------
@app.route('/quests')
@login_required
def quests():
    reset_user_quests(current_user)
    daily_quests = Quest.query.filter_by(is_daily=True).all()
    weekly_quests = Quest.query.filter_by(is_weekly=True).all()
    # İstifadəçinin görəv qeydlərini dict-ə yığ
    user_quests = {}
    for uq in current_user.quests:
        user_quests[uq.quest_id] = uq
    return render_template('quests.html', daily_quests=daily_quests, weekly_quests=weekly_quests, user_quests=user_quests)

@app.route('/achievements')
@login_required
def achievements():
    all_achievements = Achievement.query.all()
    earned_ids = [ua.achievement_id for ua in current_user.achievements]
    # Şablonda asanlıq üçün earned_achievements dict
    earned_achievements = {ach.id: (ach.id in earned_ids) for ach in all_achievements}
    return render_template('achievements.html', all_achievements=all_achievements, earned_achievements=earned_achievements)

# ---------- ADMIN ----------
@app.route('/admin')
@login_required
@admin_required
def admin():
    all_news = News.query.all()
    all_manga = Manga.query.all()
    return render_template('admin.html', all_news=all_news, all_manga=all_manga)

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
        else:
            flash('Şəkil formatı dəstəklənmir, URL istifadə ediləcək')
    if title and content:
        if not image_url:
            image_url = get_image_url(title)
        news = News(title=title, content=content, category=category, image_url=image_url, author_id=current_user.id)
        db.session.add(news)
        db.session.commit()
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

@app.route('/admin/delete-news/<int:news_id>')
@login_required
@admin_required
def delete_news(news_id):
    news = News.query.get_or_404(news_id)
    db.session.delete(news)
    db.session.commit()
    return redirect(url_for('admin'))

@app.route('/admin/delete-manga/<int:manga_id>')
@login_required
@admin_required
def delete_manga(manga_id):
    manga = Manga.query.get_or_404(manga_id)
    db.session.delete(manga)
    db.session.commit()
    return redirect(url_for('admin'))
@app.route('/upload-gif', methods=['POST'])
@login_required
def upload_gif():
    url = request.form.get('gif_url', '').strip()
    if url and url.startswith(('http://', 'https://')):
        gif = Gif(url=url, uploaded_by=current_user.id)
        db.session.add(gif)
        db.session.commit()
        flash('GIF əlavə olundu')
    else:
        flash('Düzgün URL daxil edin')
    return redirect(url_for('community'))

# ---------- INIT ----------
def init_db():
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', email='admin@midigitalverse.com', password_hash=generate_password_hash('admin123'), is_admin=True, points=100)
            db.session.add(admin)
            db.session.commit()
            print("Admin istifadəçi yaradıldı: admin / admin123")
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
        # Xəta Otağı yarat (əgər yoxdursa)
        if Room.query.filter_by(name='Xəta Otağı').first() is None:
            admin = User.query.filter_by(username='admin').first()
            if admin:
                error_room = Room(name='Xəta Otağı', news_id=None, creator_id=admin.id)
                db.session.add(error_room)
                db.session.commit()
                print("Xəta Otağı yaradıldı.")
        if Title.query.count() == 0:
            titles = [
                Title(name="Başlanğıc", description="İlk addım", color="white", rarity="common", required_xp=0),
                Title(name="Təcrübəli", description="100 XP", color="green", rarity="uncommon", required_xp=100),
                Title(name="Usta", description="500 XP", color="blue", rarity="rare", required_xp=500),
                Title(name="Epik", description="1500 XP", color="purple", rarity="epic", required_xp=1500, hidden=True),
                Title(name="Əfsanəvi", description="Yalnız bir nəfər", color="yellow", rarity="legendary", required_xp=5000, hidden=True, unique_legendary=True),
                Title(name="Admin", description="Sayt rəhbəri", color="red", rarity="admin", required_xp=0)
            ]
            db.session.add_all(titles)
            db.session.commit()
        seed_quests_and_achievements()

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)