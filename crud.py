from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from models import User, Message, Post, Comment, Like, Notification
from datetime import datetime, timedelta

# ------------------------ الشات القديم (كما هو) ------------------------ #

def create_message(db: Session, sender: str, receiver: str, content: str, timestamp: str = None):
    if timestamp:
        try:
            timestamp = datetime.fromisoformat(timestamp)
        except ValueError:
            timestamp = datetime.utcnow()
    else:
        timestamp = datetime.utcnow()

    message = Message(
        sender=sender,
        receiver=receiver,
        content=content,
        timestamp=timestamp
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message

def get_all_messages(db: Session):
    return db.query(Message).order_by(Message.timestamp.desc()).all()

def get_all_users(db: Session):
    return db.query(User).all()

def get_user(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()

def create_user(db: Session, username: str):
    user = User(username=username)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

# ------------------------ ميزة البوستات اليومية ------------------------ #

def create_post(db: Session, user_id: int, content: str):
    today = datetime.utcnow().date()

    # ✅ تحقق إن المستخدم نشر اليوم
    existing_post = db.query(Post).filter(
        Post.user_id == user_id,
        func.date(Post.timestamp) == today
    ).first()
    if existing_post:
        raise Exception("User already posted today.")

    # ✅ تحقق من حد 20 بوست يوميًا على مستوى السيرفر
    post_count_today = db.query(Post).filter(
        func.date(Post.timestamp) == today
    ).count()
    if post_count_today >= 20:
        raise Exception("Daily post limit for the server reached.")

    post = Post(user_id=user_id, content=content)
    db.add(post)
    db.commit()
    db.refresh(post)
    return post

def get_today_posts(db: Session):
    today = datetime.utcnow().date()
    return db.query(Post).filter(func.date(Post.timestamp) == today).order_by(Post.timestamp.desc()).all()

def delete_old_posts(db: Session):
    today = datetime.utcnow().date()
    db.query(Post).filter(Post.timestamp < today).delete()
    db.commit()

# ------------------------ تعليقات ------------------------ #

def add_comment(db: Session, user_id: int, post_id: int, content: str):
    comment = Comment(user_id=user_id, post_id=post_id, content=content)
    db.add(comment)
    db.commit()
    db.refresh(comment)

    # ✅ إشعار لصاحب البوست
    post = db.query(Post).filter(Post.id == post_id).first()
    if post and post.user_id != user_id:
        create_notification(db, post.user_id, f"{get_user(db, user_id).username} علق على بوستك")

    return comment

def get_comments_for_post(db: Session, post_id: int):
    return db.query(Comment).filter(Comment.post_id == post_id).order_by(Comment.timestamp.asc()).all()

# ------------------------ لايكات ------------------------ #

def like_post(db: Session, user_id: int, post_id: int):
    # ✅ لا تكرر اللايك
    existing_like = db.query(Like).filter_by(user_id=user_id, post_id=post_id).first()
    if existing_like:
        return existing_like

    like = Like(user_id=user_id, post_id=post_id)
    db.add(like)
    db.commit()
    db.refresh(like)

    # ✅ إشعار لصاحب البوست
    post = db.query(Post).filter(Post.id == post_id).first()
    if post and post.user_id != user_id:
        create_notification(db, post.user_id, f"{get_user(db, user_id).username} عمل لايك على بوستك")

    return like

def count_likes_for_post(db: Session, post_id: int):
    return db.query(Like).filter(Like.post_id == post_id).count()

# ------------------------ إشعارات ------------------------ #

def create_notification(db: Session, user_id: int, message: str):
    notification = Notification(user_id=user_id, message=message)
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification

def get_notifications(db: Session, user_id: int):
    return db.query(Notification).filter_by(user_id=user_id).order_by(Notification.timestamp.desc()).all()

def mark_notifications_read(db: Session, user_id: int):
    db.query(Notification).filter_by(user_id=user_id).update({"is_read": 1})
    db.commit()
