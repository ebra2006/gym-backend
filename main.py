from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import SessionLocal, engine, Base
from typing import List
from datetime import datetime
import crud
from models import User, Message

Base.metadata.create_all(bind=engine)
app = FastAPI()

# ✅ ذاكرة مؤقتة لحالة الكتابة typing
typing_status = {}

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ✅ مخططات الإدخال
class UserCreate(BaseModel):
    username: str

class MessageCreate(BaseModel):
    sender: str
    receiver: str
    content: str
    timestamp: str | None = None  # ✅ التوقيت من الجهاز (اختياري)


class TypingStatus(BaseModel):
    user: str
    typing: bool

# ✅ مخططات الإخراج
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
    timestamp: datetime  # ← كان str ← صلحناه لـ datetime

    class Config:
        orm_mode = True

# ✅ نقاط النهاية

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

# ✅ نقطة النهاية لحفظ حالة الكتابة
@app.post("/typing")
def update_typing_status(data: TypingStatus):
    typing_status[data.user.lower()] = data.typing
    return {"message": "updated"}

# ✅ نقطة النهاية للحصول على حالة الكتابة
@app.get("/typing")
def get_typing_status(user: str):
    status = typing_status.get(user.lower(), False)
    return {"typing": status}
