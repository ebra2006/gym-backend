from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi_utils.tasks import repeat_every
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import SessionLocal, engine, Base
from typing import List
from datetime import datetime
import crud
from models import User, Message, Post, Comment, Like, Notification

Base.metadata.create_all(bind=engine)
app = FastAPI()

typing_status = {}

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ======= مخططات الإدخال =======
class UserRegister(BaseModel):
    username: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str


class UserCreate(BaseModel):
    username: str

class MessageCreate(BaseModel):
    sender: str
    receiver: str
    content: str
    timestamp: str | None = None

class TypingStatus(BaseModel):
    user: str
    typing: bool

class PostCreate(BaseModel):
    user_id: int
    content: str

class CommentCreate(BaseModel):
    user_id: int
    post_id: int
    content: str

class LikeCreate(BaseModel):
    user_id: int
    post_id: int

class PostUpdate(BaseModel):
    content: str

# ======= مخططات الإخراج =======

class UserOut(BaseModel):
    id: int
    username: str
    class Config:
        orm_mode = True

class MessageOut(BaseModel):
    id: int
    sender: str
    receiver: str
    content: str
    timestamp: datetime
    class Config:
        orm_mode = True

class PostOut(BaseModel):
    id: int
    user_id: int
    content: str
    timestamp: datetime
    class Config:
        orm_mode = True

class CommentOut(BaseModel):
    id: int
    user_id: int
    post_id: int
    content: str
    timestamp: datetime
    class Config:
        orm_mode = True

class NotificationOut(BaseModel):
    id: int
    user_id: int
    message: str
    timestamp: datetime
    is_read: int
    class Config:
        orm_mode = True

# ======= نقاط النهاية القديمة (شات) =======

@app.post("/register", response_model=UserOut)
def register(user: UserRegister, db: Session = Depends(get_db)):
    if crud.get_user_by_username(db, user.username):
        raise HTTPException(status_code=400, detail="Username already exists")
    return crud.create_user(db, user.username, user.password)

@app.post("/login", response_model=UserOut)
def login(user: UserLogin, db: Session = Depends(get_db)):
    authenticated_user = crud.verify_user(db, user.username, user.password)
    if not authenticated_user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return authenticated_user

@app.get("/users", response_model=List[UserOut])
def list_users(db: Session = Depends(get_db)):
    return crud.get_all_users(db)

@app.post("/messages", response_model=MessageOut)
def send_message(msg: MessageCreate, db: Session = Depends(get_db)):
    return crud.create_message(
        db,
        msg.sender,
        msg.receiver,
        msg.content,
        msg.timestamp
    )

@app.get("/messages", response_model=List[MessageOut])
def list_messages(db: Session = Depends(get_db)):
    return crud.get_all_messages(db)

@app.post("/typing")
def update_typing_status(data: TypingStatus):
    typing_status[data.user.lower()] = data.typing
    return {"message": "updated"}

@app.get("/typing")
def get_typing_status(user: str):
    status = typing_status.get(user.lower(), False)
    return {"typing": status}

# ======= نقاط نهاية البوستات اليومية مع التفاصيل =======

@app.post("/posts", response_model=PostOut)
def create_post(post: PostCreate, db: Session = Depends(get_db)):
    try:
        return crud.create_post(db, post.user_id, post.content)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/posts")
def get_posts(current_user_id: int = Query(...), db: Session = Depends(get_db)):
    return crud.get_posts_with_details(db, current_user_id)

# ======= نقاط نهاية التعليقات =======

@app.post("/comments", response_model=CommentOut)
def comment_on_post(data: CommentCreate, db: Session = Depends(get_db)):
    return crud.add_comment(db, data.user_id, data.post_id, data.content)

@app.get("/comments/{post_id}", response_model=List[CommentOut])
def get_comments(post_id: int, db: Session = Depends(get_db)):
    return crud.get_comments_for_post(db, post_id)
#هنااااااا
@app.put("/comments/{comment_id}")
def update_comment(comment_id: int, new_content: str = Query(...), user_id: int = Query(...), db: Session = Depends(get_db)):
    try:
        return crud.edit_comment(db, comment_id, user_id, new_content)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/comments/{comment_id}")
def delete_comment(comment_id: int, user_id: int = Query(...), db: Session = Depends(get_db)):
    try:
        return crud.delete_comment(db, comment_id, user_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ======= نقاط نهاية اللايكات =======

@app.post("/likes")
def like_post(data: LikeCreate, db: Session = Depends(get_db)):
    return crud.like_post(db, data.user_id, data.post_id)

@app.get("/likes/{post_id}")
def count_likes(post_id: int, db: Session = Depends(get_db)):
    return {"likes": crud.count_likes_for_post(db, post_id)}
#هنااااااا
@app.delete("/likes")
def unlike_post(user_id: int = Query(...), post_id: int = Query(...), db: Session = Depends(get_db)):
    try:
        return crud.remove_like(db, user_id, post_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ======= نقاط نهاية الإشعارات =======

@app.get("/notifications/{user_id}", response_model=List[NotificationOut])
def get_notifications(user_id: int, db: Session = Depends(get_db)):
    return crud.get_notifications(db, user_id)

@app.post("/notifications/mark-read/{user_id}")
def mark_notifications(user_id: int, db: Session = Depends(get_db)):
    crud.mark_notifications_read(db, user_id)
    return {"message": "Notifications marked as read."}

# ======= نقاط نهاية تعديل وحذف البوست =======

@app.put("/posts/{post_id}")
def edit_post(post_id: int, data: PostUpdate, user_id: int = Query(...), db: Session = Depends(get_db)):
    try:
        updated_post = crud.update_post(db, post_id, user_id, data.content)
        return updated_post
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/posts/{post_id}")
def remove_post(post_id: int, user_id: int = Query(...), db: Session = Depends(get_db)):
    try:
        return crud.delete_post(db, post_id, user_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ======= حذف البوستات القديمة تلقائيًا يوميًا =======

@app.on_event("startup")
@repeat_every(seconds=60 * 60 * 24)  # كل 24 ساعة
def daily_post_cleanup_task() -> None:
    db = SessionLocal()
    crud.delete_old_posts(db)
    db.close()
