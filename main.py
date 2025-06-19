from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime
from typing import List, Dict
import os
import json

app = FastAPI()

# ======== الاستخدام ==========

class UsageData(BaseModel):
    device_id: str
    page: str
    event_type: str
    timestamp: str
    duration: int

@app.post("/track")
def track_usage(data: UsageData):
    with open("usage_log.txt", "a") as f:
        log = f"[{datetime.now()}] {data.device_id} | {data.event_type} | {data.page} | {data.duration}s\n"
        f.write(log)
    return {"status": "received"}

# ========== المستخدمون ==========

USERS_FILE = "users.txt"

def load_users() -> List[str]:
    if not os.path.exists(USERS_FILE):
        return []
    with open(USERS_FILE, "r") as f:
        return [line.strip() for line in f.readlines()]

def save_user(username: str):
    with open(USERS_FILE, "a") as f:
        f.write(username + "\n")

@app.post("/register")
def register_user(username: str):
    username = username.lower()
    users = load_users()
    if username in users:
        raise HTTPException(status_code=400, detail="Username already taken")
    save_user(username)
    return {"message": "Username registered successfully"}

@app.get("/users")
def get_all_usernames():
    return load_users()

# ========== البوستات ==========

class Post(BaseModel):
    username: str
    content: str
    timestamp: str = datetime.now().isoformat()

posts: List[Post] = []

@app.post("/posts")
def create_post(post: Post):
    posts.append(post)
    return {"message": "Post added successfully", "total_posts": len(posts)}

@app.get("/posts")
def get_all_posts():
    return posts

# ========== الشات ==========

class Message(BaseModel):
    sender: str
    receiver: str
    content: str
    timestamp: str = datetime.now().isoformat()

MESSAGES_FILE = "messages.txt"
messages: List[Message] = []

# تحميل الرسائل من الملف عند تشغيل السيرفر
def load_messages_from_file():
    global messages
    if os.path.exists(MESSAGES_FILE):
        with open(MESSAGES_FILE, "r") as f:
            messages_data = json.load(f)
            messages = [Message(**msg) for msg in messages_data]

# حفظ رسالة واحدة في الملف
def save_message_to_file(message: Message):
    # نحمل القائمة الحالية ثم نضيف الرسالة الجديدة
    current = []
    if os.path.exists(MESSAGES_FILE):
        with open(MESSAGES_FILE, "r") as f:
            current = json.load(f)

    current.append(message.dict())
    with open(MESSAGES_FILE, "w") as f:
        json.dump(current, f, indent=2)

@app.on_event("startup")
def on_startup():
    load_messages_from_file()

@app.post("/messages")
def send_message(message: Message):
    messages.append(message)
    save_message_to_file(message)
    return {"message": "Message sent and saved", "total_messages": len(messages)}

@app.get("/messages")
def get_all_messages():
    return [msg.dict() for msg in messages]

# ========== الكتابة الآن ==========

class TypingStatus(BaseModel):
    user: str
    typing: bool

typing_status: Dict[str, bool] = {}

@app.post("/typing")
def update_typing_status(status: TypingStatus):
    typing_status[status.user] = status.typing
    return {"typing": status.typing}

@app.get("/typing")
def get_typing_status(user: str):
    return {"typing": typing_status.get(user, False)}
