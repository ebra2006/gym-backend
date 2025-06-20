from sqlmodel import Session, select
from database import engine
from models import User, Message

def get_user(username: str) -> User | None:
    with Session(engine) as session:
        return session.exec(select(User).where(User.username == username)).first()

def register_user(username: str) -> bool:
    with Session(engine) as session:
        if get_user(username):
            return False
        session.add(User(username=username))
        session.commit()
        return True

def get_all_users():
    with Session(engine) as session:
        return session.exec(select(User)).all()

def delete_user(username: str) -> bool:
    with Session(engine) as session:
        user = get_user(username)
        if not user:
            return False
        user.banned = True
        session.add(user)
        session.commit()
        return True

def unban_user(username: str) -> bool:
    with Session(engine) as session:
        user = get_user(username)
        if not user:
            return False
        user.banned = False
        session.add(user)
        session.commit()
        return True

def block_user(actor: str, target: str) -> bool:
    with Session(engine) as session:
        user = get_user(actor)
        if not user:
            return False
        blocked = user.blocked.split(",") if user.blocked else []
        if target not in blocked:
            blocked.append(target)
            user.blocked = ",".join(blocked)
            session.add(user)
            session.commit()
        return True

def unblock_user(actor: str, target: str) -> bool:
    with Session(engine) as session:
        user = get_user(actor)
        if not user:
            return False
        blocked = user.blocked.split(",") if user.blocked else []
        if target in blocked:
            blocked.remove(target)
            user.blocked = ",".join(blocked)
            session.add(user)
            session.commit()
        return True

def send_message(sender: str, receiver: str, content: str) -> bool:
    with Session(engine) as session:
        session.add(Message(sender=sender, receiver=receiver, content=content))
        session.commit()
        return True

def get_all_messages():
    with Session(engine) as session:
        return session.exec(select(Message)).all()

def delete_message(message_id: int) -> bool:
    with Session(engine) as session:
        msg = session.get(Message, message_id)
        if not msg:
            return False
        session.delete(msg)
        session.commit()
        return True
