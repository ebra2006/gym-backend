from sqlalchemy.orm import Session
from sqlalchemy import func
from models import User, Message, Post, Comment, Like, Notification
from datetime import datetime
import bcrypt

# ------------------------ تسجيل مستخدم وتسجيل دخول ------------------------ #

def create_user(db: Session, username: str, password: str):
    hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    user = User(username=username, password=hashed_pw)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def get_user_by_username(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()

def verify_user(db: Session, username: str, password: str):
    user = get_user_by_username(db, username)
    if not user:
        return None
    if bcrypt.checkpw(password.encode('utf-8'), user.password.encode('utf-8')):
        return user
    return None

# ------------------------ الشات القديم ------------------------ #

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

# ------------------------ البوستات اليومية ------------------------ #

def create_post(db: Session, user_id: int, content: str):
    today = datetime.utcnow().date()

    existing_post = db.query(Post).filter(
        Post.user_id == user_id,
        func.date(Post.timestamp) == today
    ).first()
    if existing_post:
        raise Exception("User already posted today.")

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

# ------------------------ التعليقات ------------------------ #

def add_comment(db: Session, user_id: int, post_id: int, content: str):
    comment = Comment(user_id=user_id, post_id=post_id, content=content)
    db.add(comment)
    db.commit()
    db.refresh(comment)

    # ✅ تحميل العلاقة يدويًا بعد الإضافة
    db.refresh(comment)
    comment.user = db.query(User).filter(User.id == comment.user_id).first()

    post = db.query(Post).filter(Post.id == post_id).first()
    if post and post.user_id != user_id:
        create_notification(db, post.user_id, f"{comment.user.username} علق على بوستك")

    return {
        "id": comment.id,
        "user_id": comment.user_id,
        "post_id": comment.post_id,
        "content": comment.content,
        "timestamp": comment.timestamp.isoformat(),
        "username": comment.user.username if comment.user else "مجهول"
    }

def get_comments_for_post(db: Session, post_id: int):
    return db.query(Comment).filter(Comment.post_id == post_id).order_by(Comment.timestamp.asc()).all()

#هنااااا
def edit_comment(db: Session, comment_id: int, user_id: int, new_content: str):
    comment = db.query(Comment).filter(Comment.id == comment_id, Comment.user_id == user_id).first()
    if comment:
        comment.content = new_content
        db.commit()
        db.refresh(comment)
        return comment
    raise Exception("Comment not found or not yours")


def delete_comment(db: Session, comment_id: int, user_id: int):
    comment = db.query(Comment).filter(Comment.id == comment_id, Comment.user_id == user_id).first()
    if comment:
        db.delete(comment)
        db.commit()
        return {"message": "Comment deleted"}
    raise Exception("Comment not found or not yours")

# ------------------------ اللايكات ------------------------ #

def like_post(db: Session, user_id: int, post_id: int):
    existing_like = db.query(Like).filter_by(user_id=user_id, post_id=post_id).first()
    if existing_like:
        return existing_like

    like = Like(user_id=user_id, post_id=post_id)
    db.add(like)
    db.commit()
    db.refresh(like)

    post = db.query(Post).filter(Post.id == post_id).first()
    if post and post.user_id != user_id:
        create_notification(db, post.user_id, f"{get_user(db, user_id).username} عمل لايك على بوستك")

    return like

def count_likes_for_post(db: Session, post_id: int):
    return db.query(Like).filter(Like.post_id == post_id).count()
#هناااااا
def remove_like(db: Session, user_id: int, post_id: int):
    like = db.query(Like).filter(Like.user_id == user_id, Like.post_id == post_id).first()
    if like:
        db.delete(like)
        db.commit()
        return {"message": "Like removed"}
    raise Exception("Like not found")

# ------------------------ الإشعارات ------------------------ #

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

# ------------------------ بوستات مع تفاصيل ------------------------ #

def get_posts_with_details(db: Session, current_user_id: int):
    posts = db.query(Post).order_by(Post.timestamp.desc()).all()
    result = []

    for post in posts:
        likes_count = db.query(Like).filter(Like.post_id == post.id).count()
        liked_by_user = db.query(Like).filter(Like.post_id == post.id, Like.user_id == current_user_id).first() is not None

        comments_db = db.query(Comment).filter(Comment.post_id == post.id).order_by(Comment.timestamp.asc()).all()
        comments = []
        for c in comments_db:
            comments.append({
                "id": c.id,
                "user_id": c.user_id,
                "post_id": c.post_id,
                "content": c.content,
                "timestamp": c.timestamp.isoformat(),
                "username": c.user.username if c.user else "مجهول"
            })

        result.append({
            "id": post.id,
            "user_id": post.user_id,
            "content": post.content,
            "timestamp": post.timestamp.isoformat(),
            "username": post.user.username if post.user else "مجهول",
            "likes_count": likes_count,
            "liked_by_user": liked_by_user,
            "comments": comments
        })

    posts_with_likes = [p for p in result if p["likes_count"] > 0]
    if posts_with_likes:
        posts_with_likes.sort(key=lambda x: x["likes_count"], reverse=True)
        no_likes = [p for p in result if p["likes_count"] == 0]
        import random
        random.shuffle(no_likes)
        result = posts_with_likes + no_likes
    else:
        import random
        random.shuffle(result)

    return result

# ------------------------ تعديل وحذف بوست ------------------------ #

def update_post(db: Session, post_id: int, user_id: int, new_content: str):
    post = db.query(Post).filter(Post.id == post_id, Post.user_id == user_id).first()
    if not post:
        raise Exception("Post not found or no permission to edit")
    post.content = new_content
    db.commit()
    db.refresh(post)
    return post

def delete_post(db: Session, post_id: int, user_id: int):
    post = db.query(Post).filter(Post.id == post_id, Post.user_id == user_id).first()
    if not post:
        raise Exception("Post not found or no permission to delete")
    db.delete(post)
    db.commit()
    return {"message": "Post deleted"}
