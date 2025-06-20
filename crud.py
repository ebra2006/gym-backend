from sqlalchemy.orm import Session
from models import User, Message
from datetime import datetime

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

# ✅ أضف دي عشان /users تشتغل
def get_all_users(db: Session):
    return db.query(User).all()
