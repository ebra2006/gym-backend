from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel
from datetime import datetime
from typing import List, Dict, Optional
import os
import json

app = FastAPI()

USERS_FILE = "users.json"
MESSAGES_FILE = "messages.json"
BANNED_FILE = "banned_users.json"

# ========== 🧑 المستخدمون ==========

class User(BaseModel):
    username: str
    blocked: List[str] = []

def load_users() -> List[User]:
    if not os.path.exists(USERS_FILE):
        return []
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        return [User(**user) for user in json.load(f)]

def save_users(users: List[User]):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump([user.dict() for user in users], f, indent=2, ensure_ascii=False)

def get_user(username: str, users: List[User]) -> Optional[User]:
    return next((user for user in users if user.username == username), None)

def load_banned_users() -> List[str]:
    if not os.path.exists(BANNED_FILE):
        return []
    with open(BANNED_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_banned_users(banned: List[str]):
    with open(BANNED_FILE, "w", encoding="utf-8") as f:
        json.dump(banned, f, indent=2, ensure_ascii=False)

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

@app.post("/delete_user")
async def delete_user(request: Request):
    form = await request.form()
    username = form.get("username")
    users = load_users()
    users = [u for u in users if u.username != username]
    save_users(users)

    banned = load_banned_users()
    if username not in banned:
        banned.append(username)
        save_banned_users(banned)

    return RedirectResponse(url="/admin", status_code=303)

@app.post("/unban_user")
async def unban_user(request: Request):
    form = await request.form()
    username = form.get("username")
    banned = load_banned_users()
    if username in banned:
        banned.remove(username)
        save_banned_users(banned)
    return RedirectResponse(url="/admin", status_code=303)

@app.post("/admin_action")
async def admin_action(request: Request):
    form = await request.form()
    actor = form.get("actor")
    target = form.get("target")
    action = form.get("action")

    users = load_users()
    user = get_user(actor, users)
    if not user:
        return HTMLResponse("❌ المستخدم غير موجود", status_code=404)

    if action == "block" and target not in user.blocked:
        user.blocked.append(target)
    elif action == "unblock" and target in user.blocked:
        user.blocked.remove(target)

    save_users(users)
    return RedirectResponse(url="/admin", status_code=303)

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
            messages.clear()
            messages.extend([Message(**msg) for msg in json.load(f)])

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
    banned = load_banned_users()
    if message.sender in banned:
        raise HTTPException(status_code=403, detail="🚫 تم حظرك من إرسال الرسائل")

    users = load_users()
    receiver = get_user(message.receiver, users)
    if receiver and message.sender in receiver.blocked:
        raise HTTPException(status_code=403, detail="❌ تم حظرك من هذا المستخدم")

    messages.append(message)
    save_messages()
    return {"message": "Message sent", "total_messages": len(messages)}

@app.delete("/messages/{index}")
def delete_message(index: int):
    try:
        messages.pop(index)
        save_messages()
        return {"message": "Message deleted"}
    except IndexError:
        raise HTTPException(status_code=404, detail="Message not found")

# ========== لوحة التحكم ==========

@app.get("/admin", response_class=HTMLResponse)
def admin_panel():
    users = load_users()
    banned = load_banned_users()
    usernames = [u.username for u in users]

    users_html = ""
    for user in users:
        options = "".join(f"<option value='{u}'>{u}</option>" for u in usernames if u != user.username)
        blocked = ', '.join(user.blocked) if user.blocked else 'لا أحد'

        users_html += f"""
        <li>
            <b>👤 {user.username}</b> - المحظورين: {blocked}
            <form method="post" action="/delete_user" style="display:inline;">
                <input type="hidden" name="username" value="{user.username}">
                <button type="submit" style="color:red;">🗑 حذف</button>
            </form>
            <form method="post" action="/admin_action" style="display:inline;">
                <input type="hidden" name="actor" value="{user.username}">
                <select name="target">{options}</select>
                <input type="hidden" name="action" value="block">
                <button type="submit">🚫 حظر</button>
            </form>
            <form method="post" action="/admin_action" style="display:inline;">
                <input type="hidden" name="actor" value="{user.username}">
                <select name="target">{options}</select>
                <input type="hidden" name="action" value="unblock">
                <button type="submit">✅ فك الحظر</button>
            </form>
        </li>
        """

    banned_html = "".join(f"""
        <li>
            🔒 {username}
            <form method="post" action="/unban_user" style="display:inline;">
                <input type="hidden" name="username" value="{username}">
                <button type="submit">🔓 رفع الحظر</button>
            </form>
        </li>
    """ for username in banned)

    messages_html = "".join(
        f"<li>{msg.timestamp} | <b>{msg.sender}</b> → <b>{msg.receiver}</b>: {msg.content}</li>"
        for msg in messages
    )

    return f"""
    <html lang="ar" dir="rtl">
    <head><title>لوحة التحكم</title></head>
    <body style="font-family:Arial">
        <h2>🧑‍💼 المستخدمون</h2>
        <ul>{users_html}</ul>
        <hr>
        <h2>🚫 قائمة المحظورين نهائيًا</h2>
        <ul>{banned_html or '<li>لا يوجد</li>'}</ul>
        <hr>
        <h2>💬 الرسائل</h2>
        <ul>{messages_html}</ul>
    </body>
    </html>
    """
