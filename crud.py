from sqlalchemy.orm import Session
from models import User, Message
from datetime import datetime

def create_user(db: Session, username: str):
    user = User(username=username.lower())
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def get_user(db: Session, username: str):
    return db.query(User).filter(User.username == username.lower()).first()

def get_all_users(db: Session):
    return db.query(User).all()

def create_message(db: Session, sender: str, receiver: str, content: str):
    message = Message(sender=sender, receiver=receiver, content=content, timestamp=datetime.utcnow())
    db.add(message)
    db.commit()
    db.refresh(message)
    return message

def get_all_messages(db: Session):
    return db.query(Message).order_by(Message.timestamp.desc()).all()
