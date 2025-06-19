from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime
from typing import List
import os

app = FastAPI()

# ========== تتبع الاستخدام ==========
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

messages: List[Message] = []

@app.post("/messages")
def send_message(message: Message):
    messages.append(message)
    return {"message": "Message sent successfully", "total_messages": len(messages)}

@app.get("/messages")
def get_all_messages():
    return messages
