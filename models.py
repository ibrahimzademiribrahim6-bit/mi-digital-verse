from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    password_hash = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    points = db.Column(db.Integer, default=0)
    streak = db.Column(db.Integer, default=0)
    last_login_date = db.Column(db.String(20), default='')
    avatar = db.Column(db.String(200), default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    title_id = db.Column(db.Integer, db.ForeignKey('title.id'), nullable=True)
    news_read_count = db.Column(db.Integer, default=0)
    likes_count = db.Column(db.Integer, default=0)
    showcase1_id = db.Column(db.Integer, db.ForeignKey('title.id'), nullable=True)
    showcase2_id = db.Column(db.Integer, db.ForeignKey('title.id'), nullable=True)
    showcase3_id = db.Column(db.Integer, db.ForeignKey('title.id'), nullable=True)
    bio = db.Column(db.Text, default='')
    twitter_link = db.Column(db.String(200), default='')
    instagram_link = db.Column(db.String(200), default='')
    discord_link = db.Column(db.String(200), default='')
    is_banned = db.Column(db.Boolean, default=False)
    banned_until = db.Column(db.DateTime, nullable=True)
    banned_reason = db.Column(db.String(200), default='')
    is_muted = db.Column(db.Boolean, default=False)
    muted_until = db.Column(db.DateTime, nullable=True)
    muted_reason = db.Column(db.String(200), default='')

    title = db.relationship('Title', foreign_keys=[title_id])
    showcase1 = db.relationship('Title', foreign_keys=[showcase1_id])
    showcase2 = db.relationship('Title', foreign_keys=[showcase2_id])
    showcase3 = db.relationship('Title', foreign_keys=[showcase3_id])
    rooms = db.relationship('Room', backref='creator', lazy=True)
    posts = db.relationship('Post', backref='user', lazy=True)
    achievements = db.relationship('UserAchievement', backref='user', lazy=True)
    notifications = db.relationship('Notification', backref='user', lazy=True)
    quests = db.relationship('UserQuest', backref='user_quest', lazy=True)
    user_titles = db.relationship('UserTitle', backref='user', lazy=True)

    def get_level(self):
        return self.points // 100 + 1

    def get_next_level_xp(self):
        return 100 * self.get_level()

    def get_level_progress(self):
        return self.points % 100


class News(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    title_en = db.Column(db.String(200), nullable=True)
    content = db.Column(db.Text, nullable=False)
    content_en = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(50), default='Ümumi')
    image_url = db.Column(db.String(500), default='')
    views = db.Column(db.Integer, default=0)
    likes = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default='draft')
    published_at = db.Column(db.DateTime, default=datetime.utcnow)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    author = db.relationship('User', backref='news_authored')
    rooms = db.relationship('Room', backref='news', lazy=True)
    blocks = db.relationship('NewsBlock', backref='news', lazy=True, cascade="all, delete-orphan")


class Manga(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    title_en = db.Column(db.String(200), nullable=True)
    description = db.Column(db.Text, nullable=False)
    description_en = db.Column(db.Text, nullable=True)
    type = db.Column(db.String(50), default='anime')
    cover_url = db.Column(db.String(500), default='')
    rating = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(50), default='Davam edir')
    chapters = db.Column(db.Integer, default=0)
    views = db.Column(db.Integer, default=0)
    likes = db.Column(db.Integer, default=0)
    published_at = db.Column(db.DateTime, default=datetime.utcnow)


class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    news_id = db.Column(db.Integer, db.ForeignKey('news.id'), nullable=True)
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    posts = db.relationship('Post', backref='room', lazy=True)


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_spoiler = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    likes = db.Column(db.Integer, default=0)
    parent_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=True)

    replies = db.relationship('Post', backref=db.backref('parent', remote_side=[id]), lazy=True)


class Title(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    description = db.Column(db.String(200), default='')
    color = db.Column(db.String(20), default='white')
    rarity = db.Column(db.String(20), default='common')
    hidden = db.Column(db.Boolean, default=False)
    condition_type = db.Column(db.String(50), default='xp')
    condition_value = db.Column(db.Integer, default=0)
    required_xp = db.Column(db.Integer, default=0)
    unique_legendary = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class UserTitle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title_id = db.Column(db.Integer, db.ForeignKey('title.id'), nullable=False)
    earned_at = db.Column(db.DateTime, default=datetime.utcnow)

    title = db.relationship('Title', backref='user_titles')


class Achievement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.String(200), default='')
    badge_icon = db.Column(db.String(50), default='🏅')
    requirement_type = db.Column(db.String(50), default='xp')
    requirement_value = db.Column(db.Integer, default=1)
    hidden = db.Column(db.Boolean, default=False)


class UserAchievement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    achievement_id = db.Column(db.Integer, db.ForeignKey('achievement.id'), nullable=False)
    earned_at = db.Column(db.DateTime, default=datetime.utcnow)

    achievement = db.relationship('Achievement', backref='user_achievements', lazy=True)


class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.String(200), nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class NewsLike(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    news_id = db.Column(db.Integer, db.ForeignKey('news.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Quest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.String(200), default='')
    requirement_type = db.Column(db.String(50), default='news_read')
    target_value = db.Column(db.Integer, default=1)
    reward_xp = db.Column(db.Integer, default=10)
    is_daily = db.Column(db.Boolean, default=False)
    is_weekly = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class UserQuest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    quest_id = db.Column(db.Integer, db.ForeignKey('quest.id'), nullable=False)
    progress = db.Column(db.Integer, default=0)
    completed = db.Column(db.Boolean, default=False)
    last_reset_date = db.Column(db.String(20), default='')

    quest = db.relationship('Quest', backref='user_quests')


class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reporter_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    target_type = db.Column(db.String(20), nullable=False)
    target_id = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.String(200), default='')
    handled = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    reporter = db.relationship('User', foreign_keys=[reporter_id], backref='reports')


class NewsBlock(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    news_id = db.Column(db.Integer, db.ForeignKey('news.id'), nullable=False)
    block_type = db.Column(db.String(20), nullable=False)
    title_az = db.Column(db.String(200), default='')
    title_en = db.Column(db.String(200), default='')
    text_content_az = db.Column(db.Text, default='')
    text_content_en = db.Column(db.Text, default='')
    image_url = db.Column(db.String(500), default='')
    layout = db.Column(db.String(20), default='stack')
    order = db.Column(db.Integer, default=0)