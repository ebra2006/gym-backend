from fastapi import FastAPI, HTTPException, Depends, Query, WebSocket, WebSocketDisconnect
from fastapi_utils.tasks import repeat_every
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import SessionLocal, engine, Base
from typing import List
from datetime import datetime
import crud
from models import User, Message, Post, Comment, Like, Notification
import json

Base.metadata.create_all(bind=engine)
app = FastAPI()

typing_status = {}

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ===== WebSocket connection manager =====

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        data_text = json.dumps(message)
        for connection in self.active_connections:
            try:
                await connection.send_text(data_text)
            except:
                # ممكن تحذف الاتصال لو تعذر الإرسال
                self.disconnect(connection)

manager = ConnectionManager()

@app.websocket("/ws/updates")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # مجرد استقبال للحفاظ على الاتصال، لا نستخدم الرسائل الواردة هنا
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# ======= مخططات الإدخال =======

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

class CommentUpdate(BaseModel):
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
def register(user: UserCreate, db: Session = Depends(get_db)):
    if crud.get_user(db, user.username):
        raise HTTPException(status_code=400, detail="Username already exists")
    return crud.create_user(db, user.username)

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
        new_post = crud.create_post(db, post.user_id, post.content)
        # بث التحديث لجميع المتصلين
        import asyncio
        asyncio.create_task(manager.broadcast({
            "type": "post_created",
            "post_id": new_post.id,
            "user_id": new_post.user_id,
            "content": new_post.content,
            "timestamp": new_post.timestamp.isoformat()
        }))
        return new_post
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/posts")
def get_posts(current_user_id: int = Query(...), db: Session = Depends(get_db)):
    return crud.get_posts_with_details(db, current_user_id)

@app.put("/posts/{post_id}")
def edit_post(post_id: int, data: PostUpdate, user_id: int = Query(...), db: Session = Depends(get_db)):
    try:
        updated_post = crud.update_post(db, post_id, user_id, data.content)
        import asyncio
        asyncio.create_task(manager.broadcast({
            "type": "post_updated",
            "post_id": updated_post.id,
            "user_id": updated_post.user_id,
            "content": updated_post.content,
            "timestamp": updated_post.timestamp.isoformat()
        }))
        return updated_post
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/posts/{post_id}")
def remove_post(post_id: int, user_id: int = Query(...), db: Session = Depends(get_db)):
    try:
        # تحقق إن البوست ينتمي للمستخدم
        post = db.query(Post).filter(Post.id == post_id, Post.user_id == user_id).first()
        if not post:
            raise HTTPException(status_code=403, detail="No permission to delete this post or post not found")
        crud.delete_post(db, post_id, user_id)

        import asyncio
        asyncio.create_task(manager.broadcast({
            "type": "post_deleted",
            "post_id": post_id
        }))
        return {"message": "Post deleted"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ======= نقاط نهاية التعليقات =======

@app.post("/comments", response_model=CommentOut)
def comment_on_post(data: CommentCreate, db: Session = Depends(get_db)):
    comment = crud.add_comment(db, data.user_id, data.post_id, data.content)
    import asyncio
    asyncio.create_task(manager.broadcast({
        "type": "comment_created",
        "comment_id": comment.id,
        "post_id": comment.post_id,
        "user_id": comment.user_id,
        "content": comment.content,
        "timestamp": comment.timestamp.isoformat()
    }))
    return comment

@app.get("/comments/{post_id}", response_model=List[CommentOut])
def get_comments(post_id: int, db: Session = Depends(get_db)):
    return crud.get_comments_for_post(db, post_id)

@app.put("/comments/{comment_id}")
def edit_comment(comment_id: int, data: CommentUpdate, user_id: int = Query(...), db: Session = Depends(get_db)):
    try:
        updated_comment = crud.update_comment(db, comment_id, user_id, data.content)
        import asyncio
        asyncio.create_task(manager.broadcast({
            "type": "comment_updated",
            "comment_id": updated_comment.id,
            "post_id": updated_comment.post_id,
            "user_id": updated_comment.user_id,
            "content": updated_comment.content,
            "timestamp": updated_comment.timestamp.isoformat()
        }))
        return updated_comment
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/comments/{comment_id}")
def delete_comment(comment_id: int, user_id: int = Query(...), db: Session = Depends(get_db)):
    try:
        crud.delete_comment(db, comment_id, user_id)
        import asyncio
        asyncio.create_task(manager.broadcast({
            "type": "comment_deleted",
            "comment_id": comment_id
        }))
        return {"message": "Comment deleted"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ======= نقاط نهاية اللايكات =======

@app.post("/likes")
def like_post(data: LikeCreate, db: Session = Depends(get_db)):
    like = crud.like_post(db, data.user_id, data.post_id)
    import asyncio
    asyncio.create_task(manager.broadcast({
        "type": "like_added",
        "user_id": data.user_id,
        "post_id": data.post_id
    }))
    return like

@app.delete("/likes")
def unlike_post(user_id: int = Query(...), post_id: int = Query(...), db: Session = Depends(get_db)):
    try:
        crud.delete_like(db, user_id, post_id)
        import asyncio
        asyncio.create_task(manager.broadcast({
            "type": "like_removed",
            "user_id": user_id,
            "post_id": post_id
        }))
        return {"message": "Like removed"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/likes/{post_id}")
def count_likes(post_id: int, db: Session = Depends(get_db)):
    return {"likes": crud.count_likes_for_post(db, post_id)}

# ======= نقاط نهاية الإشعارات =======

@app.get("/notifications/{user_id}", response_model=List[NotificationOut])
def get_notifications(user_id: int, db: Session = Depends(get_db)):
    return crud.get_notifications(db, user_id)

@app.post("/notifications/mark-read/{user_id}")
def mark_notifications(user_id: int, db: Session = Depends(get_db)):
    crud.mark_notifications_read(db, user_id)
    return {"message": "Notifications marked as read."}

# ======= حذف البوستات القديمة تلقائيًا يوميًا =======

@app.on_event("startup")
@repeat_every(seconds=60 * 60 * 24)  # كل 24 ساعة
def daily_post_cleanup_task() -> None:
    db = SessionLocal()
    crud.delete_old_posts(db)
    db.close()
