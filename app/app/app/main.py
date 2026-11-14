import os
import hmac
import html
import logging
import sqlite3
from datetime import datetime, timezone

import httpx
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from starlette.middleware.sessions import SessionMiddleware

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("synova")

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
ADMIN_ID = os.getenv("ADMIN_ID", "").strip()
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "").strip()
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "").strip()
SESSION_SECRET = os.getenv("SESSION_SECRET", "change-this-secret")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
DATABASE_PATH = os.getenv("DATABASE_PATH", "/tmp/synova.db")

app = FastAPI(title="SYNOVA AI")

app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    https_only=True,
    same_site="lax"
)


def db():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def now():
    return datetime.now(timezone.utc).isoformat()


def init_db():
    with db() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            chat_id INTEGER,
            username TEXT,
            first_name TEXT,
            joined_at TEXT,
            last_seen TEXT
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            role TEXT,
            content TEXT,
            created_at TEXT
        )
        """)


def save_user(user, chat_id):
    uid = user.get("id")
    if not uid:
        return

    with db() as conn:
        conn.execute("""
        INSERT INTO users VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
        chat_id=excluded.chat_id,
        username=excluded.username,
        first_name=excluded.first_name,
        last_seen=excluded.last_seen
        """, (
            uid, chat_id, user.get("username"),
            user.get("first_name"), now(), now()
        ))


def save_message(uid, role, content):
    with db() as conn:
        conn.execute(
            "INSERT INTO messages(user_id,role,content,created_at) VALUES(?,?,?,?)",
            (uid, role, content[:10000], now())
        )
        conn.execute("""
        DELETE FROM messages WHERE user_id=? AND id NOT IN
        (SELECT id FROM messages WHERE user_id=? ORDER BY id DESC LIMIT 12)
        """, (uid, uid))


def get_history(uid):
    with db() as conn:
        rows = conn.execute(
            "SELECT role,content FROM messages WHERE user_id=? ORDER BY id",
            (uid,)
        ).fetchall()

    return [
        {"role": r["role"], "parts": [{"text": r["content"]}]}
        for r in rows
    ]


async def gemini_reply(uid, prompt):
    if not GEMINI_API_KEY:
        return "Gemini API Key সেট করা হয়নি।"

    contents = get_history(uid)
    contents.append({
        "role": "user",
        "parts": [{"text": prompt}]
    })

    url = (
        "https://generativelanguage.googleapis.com/"
        f"v1beta/models/{GEMINI_MODEL}:generateContent"
    )

    payload = {
        "contents": contents,
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 2048
        }
    }

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            url,
            params={"key": GEMINI_API_KEY},
            json=payload
        )

    if response.status_code != 200:
        log.error("Gemini error: %s", response.text)
        return f"Gemini API Error: {response.status_code}"

    data = response.json()

    try:
        answer = data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, TypeError):
        return "দুঃখিত, উত্তর তৈরি করা যায়নি।"

    save_message(uid, "user", prompt)
    save_message(uid, "model", answer)

    return answer


async def telegram(method, payload):
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN missing")

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"

    async with httpx.AsyncClient(timeout=40) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        return response.json()


async def send_message(chat_id, text):
    for i in range(0, len(text), 4000):
        await telegram("sendMessage", {
            "chat_id": chat_id,
            "text": text[i:i + 4000]
        })


def page(title, body):
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{html.escape(title)} - SYNOVA AI</title>
    <style>
    body {{
        background:#0b1220;
        color:#eee;
        font-family:Arial;
        padding:20px;
    }}
    .box {{
        background:#182337;
        padding:22px;
        border-radius:15px;
        margin:15px auto;
        max-width:800px;
    }}
    h1 {{color:#72d9ff}}
    input,textarea {{
        width:100%;
        padding:12px;
        margin:10px 0;
        box-sizing:border-box;
        border-radius:8px;
    }}
    button {{
        padding:12px 20px;
        background:#159c9c;
        color:white;
        border:0;
        border-radius:8px;
    }}
    </style>
    </head>
    <body>
    {body}
    </body>
    </html>
    """


@app.on_event("startup")
async def startup():
    init_db()

    host = os.getenv("RENDER_EXTERNAL_HOSTNAME", "")

    if BOT_TOKEN and WEBHOOK_SECRET and host:
        try:
            await telegram("setWebhook", {
                "url": f"https://{host}/telegram/{WEBHOOK_SECRET}"
            })
            log.info("Telegram webhook configured")
        except Exception:
            log.exception("Webhook setup failed")


@app.get("/", response_class=HTMLResponse)
async def home():
    return page("SYNOVA AI", """
    <div class="box">
    <h1>✦ SYNOVA AI</h1>
    <p>Your AI assistant is running.</p>
    <p>Telegram bot is ready.</p>
    <a href="/admin">Admin Dashboard</a>
    </div>
    """)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "SYNOVA AI"}


@app.post("/telegram/{secret}")
async def webhook(secret: str, request: Request):

    if not WEBHOOK_SECRET or not hmac.compare_digest(
        secret, WEBHOOK_SECRET
    ):
        raise HTTPException(status_code=404)

    update = await request.json()
    message = update.get("message")

    if not message or not message.get("text"):
        return {"ok": True}

    chat_id = message["chat"]["id"]
    user = message.get("from", {})
    uid = user.get("id")
    text = message["text"].strip()

    save_user(user, chat_id)

    if text.startswith("/start"):
        reply = (
            "স্বাগতম SYNOVA AI-তে! ✦\n\n"
            "যেকোনো প্রশ্ন লিখে পাঠাও।"
        )

    elif text.startswith("/help"):
        reply = "আমাকে যেকোনো প্রশ্ন করতে পারো।"

    elif text.startswith("/new"):
        with db() as conn:
            conn.execute(
                "DELETE FROM messages WHERE user_id=?",
                (uid,)
            )
        reply = "নতুন চ্যাট শুরু হয়েছে!"

    elif text.startswith("/admin"):
        if ADMIN_ID and str(uid) == ADMIN_ID:
            reply = "Admin Dashboard: " + os.getenv(
                "RENDER_EXTERNAL_URL", ""
            ) + "/admin"
        else:
            reply = "তোমার Admin Access নেই।"

    else:
        try:
            reply = await gemini_reply(uid, text)
        except Exception:
            log.exception("Chat error")
            reply = "দুঃখিত, সমস্যা হয়েছে। আবার চেষ্টা করো।"

    await send_message(chat_id, reply)

    return {"ok": True}


@app.get("/admin", response_class=HTMLResponse)
async def admin(request: Request):

    if not request.session.get("admin"):
        return page("Admin Login", """
        <div class="box">
        <h1>SYNOVA AI Admin</h1>
        <form method="post" action="/admin/login">
        <input type="password" name="password"
        placeholder="Admin Password" required>
        <button type="submit">Login</button>
        </form>
        </div>
        """)

    with db() as conn:
        users = conn.execute(
            "SELECT COUNT(*) FROM users"
        ).fetchone()[0]

        messages = conn.execute(
            "SELECT COUNT(*) FROM messages"
        ).fetchone()[0]

        rows = conn.execute(
            "SELECT user_id,username,first_name FROM users "
            "ORDER BY last_seen DESC LIMIT 30"
        ).fetchall()

    user_rows = "".join(
        f"<tr><td>{r['user_id']}</td>"
        f"<td>{html.escape(r['username'] or '')}</td>"
        f"<td>{html.escape(r['first_name'] or '')}</td></tr>"
        for r in rows
    )

    return page("Dashboard", f"""
    <div class="box">
    <h1>✦ SYNOVA AI Dashboard</h1>
    <h2>Total Users: {users}</h2>
    <h2>Total Messages: {messages}</h2>
    <h3>Recent Users</h3>
    <table>{user_rows}</table>
    </div>

    <div class="box">
    <h2>Broadcast Message</h2>
    <form method="post" action="/admin/broadcast">
    <textarea name="message" required></textarea>
    <button>Send to All Users</button>
    </form>
    <form method="post" action="/admin/logout">
    <button>Logout</button>
    </form>
    </div>
    """)


@app.post("/admin/login")
async def admin_login(
    request: Request,
    password: str = Form(...)
):
    if not ADMIN_PASSWORD:
        raise HTTPException(
            status_code=503,
            detail="ADMIN_PASSWORD not configured"
        )

    if not hmac.compare_digest(password, ADMIN_PASSWORD):
        raise HTTPException(status_code=401)

    request.session["admin"] = True
    return RedirectResponse("/admin", status_code=303)


@app.post("/admin/logout")
async def admin_logout(request: Request):
    request.session.clear()
    return RedirectResponse("/admin", status_code=303)


@app.post("/admin/broadcast")
async def broadcast(
    request: Request,
    message: str = Form(...)
):
    if not request.session.get("admin"):
        raise HTTPException(status_code=401)

    with db() as conn:
        users = conn.execute(
            "SELECT chat_id FROM users"
        ).fetchall()

    sent = 0

    for user in users:
        try:
            await send_message(user["chat_id"], message)
            sent += 1
        except Exception:
            log.exception("Broadcast failed")

    return page(
        "Broadcast",
        f"<div class='box'><h2>Sent to {sent} users</h2>"
        "<a href='/admin'>Back</a></div>"
        )
