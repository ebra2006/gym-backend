from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime
from typing import List

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

# ========== البوستات (المجتمع) ==========
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

# ========== الشات النصي ==========
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
