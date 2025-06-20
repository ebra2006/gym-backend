from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import SessionLocal, engine, Base
import crud

Base.metadata.create_all(bind=engine)
app = FastAPI()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class UserCreate(BaseModel):
    username: str

class MessageCreate(BaseModel):
    sender: str
    receiver: str
    content: str

@app.post("/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    if crud.get_user(db, user.username):
        raise HTTPException(status_code=400, detail="Username already exists")
    return crud.create_user(db, user.username)

@app.get("/users")
def list_users(db: Session = Depends(get_db)):
    return crud.get_all_users(db)

@app.post("/messages")
def send_message(msg: MessageCreate, db: Session = Depends(get_db)):
    return crud.create_message(db, msg.sender, msg.receiver, msg.content)

@app.get("/messages")
def list_messages(db: Session = Depends(get_db)):
    return crud.get_all_messages(db)
