from sqlalchemy.orm import Session
from models import User, Message
from datetime import datetime

# ✅ إنشاء رسالة جديدة
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

# ✅ استرجاع كل الرسائل
def get_all_messages(db: Session):
    return db.query(Message).order_by(Message.timestamp.desc()).all()

# ✅ استرجاع كل المستخدمين
def get_all_users(db: Session):
    return db.query(User).all()

# ✅ استرجاع مستخدم معين حسب الاسم
def get_user(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()

# ✅ إنشاء مستخدم جديد
def create_user(db: Session, username: str):
    user = User(username=username)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
