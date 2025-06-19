from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime
from typing import List, Dict, Optional
import os
import json

app = FastAPI()

# ========== 🔍 المسارات ==========
USERS_FILE = "users.json"
MESSAGES_FILE = "messages.json"

# ========== 🧑 المستخدمون ==========

class User(BaseModel):
    username: str
    blocked: List[str] = []

def load_users() -> List[User]:
    if not os.path.exists(USERS_FILE):
        return []
    with open(USERS_FILE, "r") as f:
        users_data = json.load(f)
        return [User(**user) for user in users_data]

def save_users(users: List[User]):
    with open(USERS_FILE, "w") as f:
        json.dump([user.dict() for user in users], f, indent=2)

def get_user(username: str, users: List[User]) -> Optional[User]:
    for user in users:
        if user.username == username:
            return user
    return None

@app.post("/register")
def register_user(username: str):
    username = username.lower()
    users = load_users()
    if get_user(username, users):
        raise HTTPException(status_code=400, detail="Username already exists")
    users.append(User(username=username))
    save_users(users)
    return {"message": "User registered successfully"}

@app.get("/users")
def get_all_users():
    return [user.dict() for user in load_users()]

@app.post("/block")
def block_user(current_user: str, block_user: str):
    users = load_users()
    user = get_user(current_user, users)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if block_user not in user.blocked:
        user.blocked.append(block_user)
        save_users(users)
    return {"message": f"{block_user} blocked"}

@app.post("/unblock")
def unblock_user(current_user: str, block_user: str):
    users = load_users()
    user = get_user(current_user, users)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if block_user in user.blocked:
        user.blocked.remove(block_user)
        save_users(users)
    return {"message": f"{block_user} unblocked"}

# ========== 💬 الرسائل ==========

class Message(BaseModel):
    sender: str
    receiver: str
    content: str
    timestamp: str = datetime.now().isoformat()

messages: List[Message] = []

def load_messages():
    global messages
    if os.path.exists(MESSAGES_FILE):
        with open(MESSAGES_FILE, "r") as f:
            msgs = json.load(f)
            messages.clear()
            messages.extend([Message(**msg) for msg in msgs])

def save_messages():
    with open(MESSAGES_FILE, "w") as f:
        json.dump([m.dict() for m in messages], f, indent=2)

@app.on_event("startup")
def startup():
    load_messages()

@app.get("/messages")
def get_all_messages():
    return [msg.dict() for msg in messages]

@app.post("/messages")
def send_message(message: Message):
    users = load_users()
    receiver = get_user(message.receiver, users)
    if receiver and message.sender in receiver.blocked:
        raise HTTPException(status_code=403, detail="You are blocked by this user")
    messages.append(message)
    save_messages()
    return {"message": "Message sent", "total_messages": len(messages)}

@app.delete("/messages/{index}")
def delete_message(index: int):
    try:
        messages.pop(index)
        save_messages()
        return {"message": f"Message at index {index} deleted"}
    except IndexError:
        raise HTTPException(status_code=404, detail="Message not found")

# ========== ✍️ الكتابة الآن ==========

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

# ========== 🧪 اختبار الاستخدام ==========

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
