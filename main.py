from fastapi import FastAPI, Form, Request, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from models import User
from crud import *
from database import create_db_and_tables

app = FastAPI()

@app.on_event("startup")
def startup():
    create_db_and_tables()

@app.post("/register")
def register(username: str):
    username = username.strip().lower()
    if register_user(username):
        return {"message": "تم تسجيل المستخدم"}
    raise HTTPException(status_code=400, detail="اسم المستخدم موجود بالفعل")

@app.get("/users")
def users():
    return [user.username for user in get_all_users() if not user.banned]

@app.post("/messages")
def message(sender: str, receiver: str, content: str):
    user = get_user(sender)
    if user and user.banned:
        raise HTTPException(status_code=403, detail="🚫 تم حظرك من إرسال الرسائل")

    receiver_user = get_user(receiver)
    if receiver_user and sender in receiver_user.blocked.split(","):
        raise HTTPException(status_code=403, detail="❌ تم حظرك من هذا المستخدم")

    send_message(sender, receiver, content)
    return {"message": "تم إرسال الرسالة"}

@app.get("/messages")
def messages():
    return [msg.dict() for msg in get_all_messages()]

@app.delete("/messages/{msg_id}")
def delete(msg_id: int):
    if delete_message(msg_id):
        return {"message": "تم حذف الرسالة"}
    raise HTTPException(status_code=404, detail="الرسالة غير موجودة")

@app.get("/admin", response_class=HTMLResponse)
def admin_panel():
    users = get_all_users()
    messages = get_all_messages()

    html = """
    <html dir='rtl'><head><title>لوحة التحكم</title></head><body style="font-family:Arial">
    <h2>🧑 المستخدمون</h2><ul>
    """
    for user in users:
        blocked = user.blocked if user.blocked else "لا أحد"
        html += f"""
        <li><b>{user.username}</b> | محظور نهائيًا: {"✅" if user.banned else "❌"} | المحظورين منه: {blocked}
        <form method='post' action='/block' style='display:inline'>
            <input type='hidden' name='actor' value='{user.username}'>
            <input name='target' placeholder='اسم المستخدم'>
            <button>🚫 حظر</button>
        </form>
        <form method='post' action='/unblock' style='display:inline'>
            <input type='hidden' name='actor' value='{user.username}'>
            <input name='target' placeholder='اسم المستخدم'>
            <button>✅ فك الحظر</button>
        </form>
        <form method='post' action='/delete_user' style='display:inline'>
            <input type='hidden' name='username' value='{user.username}'>
            <button style='color:red'>🗑 حذف</button>
        </form>
        <form method='post' action='/unban_user' style='display:inline'>
            <input type='hidden' name='username' value='{user.username}'>
            <button>🔓 رفع الحظر</button>
        </form>
        </li>
        """
    html += "</ul><hr><h2>💬 الرسائل</h2><ul>"
    for msg in messages:
        html += f"<li>{msg.timestamp} | <b>{msg.sender}</b> → <b>{msg.receiver}</b>: {msg.content} <a href='/delete_msg?id={msg.id}'>🗑</a></li>"
    html += "</ul></body></html>"
    return html

@app.get("/delete_msg")
def delete_via_link(id: int):
    delete_message(id)
    return RedirectResponse("/admin", status_code=303)

@app.post("/block")
async def block(request: Request):
    form = await request.form()
    block_user(form["actor"], form["target"])
    return RedirectResponse("/admin", status_code=303)

@app.post("/unblock")
async def unblock(request: Request):
    form = await request.form()
    unblock_user(form["actor"], form["target"])
    return RedirectResponse("/admin", status_code=303)

@app.post("/delete_user")
async def ban(request: Request):
    form = await request.form()
    delete_user(form["username"])
    return RedirectResponse("/admin", status_code=303)

@app.post("/unban_user")
async def unban(request: Request):
    form = await request.form()
    unban_user(form["username"])
    return RedirectResponse("/admin", status_code=303)
