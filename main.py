from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from datetime import datetime
from typing import List, Dict, Optional
import os
import json

app = FastAPI()

USERS_FILE = "users.json"
MESSAGES_FILE = "messages.json"

# ========== 🧑 المستخدمون ==========
class User(BaseModel):
    username: str
    blocked: List[str] = []

def load_users() -> List[User]:
    if not os.path.exists(USERS_FILE):
        return []
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        users_data = json.load(f)
        return [User(**user) for user in users_data]

def save_users(users: List[User]):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump([user.dict() for user in users], f, indent=2, ensure_ascii=False)

def get_user(username: str, users: List[User]) -> Optional[User]:
    return next((user for user in users if user.username == username), None)

@app.post("/register")
def register_user(username: str):
    username = username.strip().lower()
    users = load_users()
    if get_user(username, users):
        raise HTTPException(status_code=400, detail="Username already exists")
    users.append(User(username=username))
    save_users(users)
    return {"message": "User registered successfully"}

@app.get("/users")
def get_all_users():
    return [user.username for user in load_users()]

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

@app.post("/delete_user")
async def delete_user(request: Request):
    form = await request.form()
    username_to_delete = form.get("username")
    users = load_users()
    updated_users = [u for u in users if u.username != username_to_delete]
    save_users(updated_users)
    return HTMLResponse(content=f"""
        <html lang="ar" dir="rtl">
        <body style="font-family:Arial">
            <p>✅ تم حذف المستخدم: <b>{username_to_delete}</b></p>
            <a href="/admin">🔙 العودة إلى لوحة التحكم</a>
        </body>
        </html>
    """)

@app.post("/admin_action")
async def admin_action(request: Request):
    form = await request.form()
    action = form.get("action")
    target = form.get("target")
    actor = form.get("actor")

    users = load_users()
    user = get_user(actor, users)
    if not user:
        return HTMLResponse("المستخدم غير موجود", status_code=404)

    if action == "block" and target not in user.blocked:
        user.blocked.append(target)
    elif action == "unblock" and target in user.blocked:
        user.blocked.remove(target)
    save_users(users)
    return HTMLResponse(content=f"""
        <html lang="ar" dir="rtl">
        <body style="font-family:Arial">
            <p>✅ تم تنفيذ الإجراء <b>{action}</b> على <b>{target}</b> بواسطة <b>{actor}</b></p>
            <a href="/admin">🔙 العودة إلى لوحة التحكم</a>
        </body>
        </html>
    """)

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
        with open(MESSAGES_FILE, "r", encoding="utf-8") as f:
            msgs = json.load(f)
            messages.clear()
            messages.extend([Message(**msg) for msg in msgs])

def save_messages():
    with open(MESSAGES_FILE, "w", encoding="utf-8") as f:
        json.dump([m.dict() for m in messages], f, indent=2, ensure_ascii=False)

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

# ========== 🧪 تتبع الاستخدام ==========
class UsageData(BaseModel):
    device_id: str
    page: str
    event_type: str
    timestamp: str
    duration: int

@app.post("/track")
def track_usage(data: UsageData):
    with open("usage_log.txt", "a", encoding="utf-8") as f:
        log = f"[{datetime.now()}] {data.device_id} | {data.event_type} | {data.page} | {data.duration}s\n"
        f.write(log)
    return {"status": "received"}

# ========== لوحة تحكم HTML ==========
@app.get("/admin", response_class=HTMLResponse)
def admin_panel():
    users = load_users()
    users_html = "".join(
        f"""
        <li>
            👤 <b>{user.username}</b> - الحظر: {', '.join(user.blocked) if user.blocked else 'لا شيء'}
            <form method="post" action="/delete_user" style="display:inline;">
                <input type="hidden" name="username" value="{user.username}">
                <button type="submit" style="color:red;">حذف</button>
            </form>
            <form method="post" action="/admin_action" style="display:inline;">
                <input type="hidden" name="actor" value="{user.username}">
                <input type="hidden" name="target" value="testuser">
                <input type="hidden" name="action" value="block">
                <button type="submit">حظر testuser</button>
            </form>
            <form method="post" action="/admin_action" style="display:inline;">
                <input type="hidden" name="actor" value="{user.username}">
                <input type="hidden" name="target" value="testuser">
                <input type="hidden" name="action" value="unblock">
                <button type="submit">فك الحظر عن testuser</button>
            </form>
        </li>
        """ for user in users
    )

    messages_html = "".join(
        f"<li>{msg.timestamp} | <b>{msg.sender}</b> إلى <b>{msg.receiver}</b>: {msg.content}</li>"
        for msg in messages
    )

    return f"""
    <html lang="ar" dir="rtl">
    <head><title>لوحة التحكم</title></head>
    <body style="font-family:Arial">
        <h2>🧑‍💼 المستخدمون</h2>
        <ul>{users_html}</ul>
        <hr>
        <h2>💬 الرسائل</h2>
        <ul>{messages_html}</ul>
    </body>
    </html>
    """
