from fastapi import FastAPI, HTTPException, Depends, Query, WebSocket, WebSocketDisconnect
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

# ----------------- WebSocket Manager -----------------
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass

post_manager = ConnectionManager()

@app.websocket("/ws/posts")
async def post_websocket(websocket: WebSocket):
    await post_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        post_manager.disconnect(websocket)

# ----------------- Database Dependency -----------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ----------------- Schemas -----------------
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

# ----------------- Auth & Users -----------------
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

# ----------------- Messages -----------------
@app.post("/messages", response_model=MessageOut)
def send_message(msg: MessageCreate, db: Session = Depends(get_db)):
    return crud.create_message(db, msg.sender, msg.receiver, msg.content, msg.timestamp)

@app.get("/messages", response_model=List[MessageOut])
def list_messages(db: Session = Depends(get_db)):
    return crud.get_all_messages(db)

@app.post("/typing")
def update_typing_status(data: TypingStatus):
    return {"message": "updated"}

@app.get("/typing")
def get_typing_status(user: str):
    return {"typing": False}

# ----------------- Posts -----------------
@app.post("/posts", response_model=PostOut)
async def create_post(post: PostCreate, db: Session = Depends(get_db)):
    try:
        created = crud.create_post(db, post.user_id, post.content)
        await post_manager.broadcast({"action": "new_post", "post_id": created.id})
        return created
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/posts")
def get_posts(current_user_id: int = Query(...), db: Session = Depends(get_db)):
    return crud.get_posts_with_details(db, current_user_id)

@app.put("/posts/{post_id}")
async def edit_post(post_id: int, data: PostUpdate, user_id: int = Query(...), db: Session = Depends(get_db)):
    try:
        updated = crud.update_post(db, post_id, user_id, data.content)
        await post_manager.broadcast({"action": "edit_post", "post_id": updated.id})
        return updated
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/posts/{post_id}")
async def remove_post(post_id: int, user_id: int = Query(...), db: Session = Depends(get_db)):
    try:
        crud.delete_post(db, post_id, user_id)
        await post_manager.broadcast({"action": "delete_post", "post_id": post_id})
        return {"message": "Post deleted"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ----------------- Comments -----------------
@app.post("/comments", response_model=CommentOut)
async def comment_on_post(data: CommentCreate, db: Session = Depends(get_db)):
    comment = crud.add_comment(db, data.user_id, data.post_id, data.content)
    await post_manager.broadcast({"action": "new_comment", "post_id": data.post_id})
    return comment

@app.get("/comments/{post_id}", response_model=List[CommentOut])
def get_comments(post_id: int, db: Session = Depends(get_db)):
    return crud.get_comments_for_post(db, post_id)

@app.put("/comments/{comment_id}")
async def update_comment(comment_id: int, new_content: str = Query(...), user_id: int = Query(...), db: Session = Depends(get_db)):
    try:
        comment = crud.edit_comment(db, comment_id, user_id, new_content)
        await post_manager.broadcast({"action": "edit_comment", "post_id": comment.post_id})
        return comment
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/comments/{comment_id}")
async def delete_comment(comment_id: int, user_id: int = Query(...), db: Session = Depends(get_db)):
    try:
        result = crud.delete_comment(db, comment_id, user_id)
        await post_manager.broadcast({"action": "delete_comment", "comment_id": comment_id})
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ----------------- Likes -----------------
@app.post("/likes")
async def like_post(data: LikeCreate, db: Session = Depends(get_db)):
    like = crud.like_post(db, data.user_id, data.post_id)
    await post_manager.broadcast({"action": "like", "post_id": data.post_id})
    return like

@app.get("/likes/{post_id}")
def count_likes(post_id: int, db: Session = Depends(get_db)):
    return {"likes": crud.count_likes_for_post(db, post_id)}

@app.delete("/likes")
async def unlike_post(user_id: int = Query(...), post_id: int = Query(...), db: Session = Depends(get_db)):
    try:
        crud.remove_like(db, user_id, post_id)
        await post_manager.broadcast({"action": "unlike", "post_id": post_id})
        return {"message": "Like removed"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ----------------- Notifications -----------------
@app.get("/notifications/{user_id}", response_model=List[NotificationOut])
def get_notifications(user_id: int, db: Session = Depends(get_db)):
    return crud.get_notifications(db, user_id)

@app.post("/notifications/mark-read/{user_id}")
def mark_notifications(user_id: int, db: Session = Depends(get_db)):
    crud.mark_notifications_read(db, user_id)
    return {"message": "Notifications marked as read."}

# ----------------- Auto Delete Old Posts -----------------
@app.on_event("startup")
@repeat_every(seconds=60 * 60 * 24)  # كل 24 ساعة
def daily_post_cleanup_task() -> None:
    db = SessionLocal()
    try:
        crud.delete_old_posts(db)  # دالة في crud تحذف البوستات القديمة + تعليقات + لايكات
    finally:
        db.close()
