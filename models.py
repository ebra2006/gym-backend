
from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)  # 👈 تم إضافته

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    sender = Column(String, index=True)
    receiver = Column(String, index=True)
    content = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)

# ✅ جدول البوستات
class Post(Base):
    __tablename__ = "posts"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")
    comments = relationship("Comment", cascade="all, delete-orphan", passive_deletes=True)
    likes = relationship("Like", cascade="all, delete-orphan", passive_deletes=True)


# ✅ جدول التعليقات
# جدول التعليقات
class Comment(Base):
    __tablename__ = "comments"
    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("posts.id", ondelete="CASCADE"))
    user_id = Column(Integer, ForeignKey("users.id"))
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    post = relationship("Post", backref="comments")
    user = relationship("User")


# ✅ جدول اللايكات
# جدول اللايكات
class Like(Base):
    __tablename__ = "likes"
    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("posts.id", ondelete="CASCADE"))
    user_id = Column(Integer, ForeignKey("users.id"))

    post = relationship("Post", backref="likes")
    user = relationship("User")

    __table_args__ = (
        UniqueConstraint("post_id", "user_id", name="unique_like"),
    )


# ✅ جدول الإشعارات
class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))  # المستلم
    message = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    is_read = Column(Integer, default=0)
