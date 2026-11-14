# SYNOVA AI — Telegram Bot

A deployable Telegram AI chatbot starter built with FastAPI, Gemini API, SQLite and a small admin dashboard.

## Repository structure (IMPORTANT)

The `app` folder must be at the repository root. Do not upload only the files inside `app`.

```text
SYNOVA-AI/
├── app/
│   ├── __init__.py
│   └── main.py
├── .env.example
├── .gitignore
├── LICENSE
├── README.md
├── render.yaml
└── requirements.txt
```

This layout fixes `ModuleNotFoundError: No module named 'app'`.

## Deploy steps

1. Download and extract this ZIP.
2. Upload all extracted contents to the ROOT of your GitHub repository. The GitHub main page should visibly show the `app` folder, `requirements.txt`, and `render.yaml`.
3. In Render, create a Blueprint from the repository, or create a Python web service with:
   - Build command: `pip install -r requirements.txt`
   - Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Add these Environment variables in Render:
   - `BOT_TOKEN`: token from Telegram BotFather
   - `GEMINI_API_KEY`: key from Google AI Studio
   - `ADMIN_ID`: your numeric Telegram user ID
   - `ADMIN_PASSWORD`: a strong password for the web dashboard
   - `WEBHOOK_SECRET`: long random secret (Blueprint can generate it)
   - `SESSION_SECRET`: long random secret (Blueprint can generate it)
5. Deploy. Visit `https://YOUR-SERVICE.onrender.com/health`; it should show status `ok`.
6. Open your Telegram bot and send `/start`.
7. Admin dashboard: `https://YOUR-SERVICE.onrender.com/admin`

## Bot commands

- `/start` — welcome message
- `/help` — help
- `/new` — clear the stored conversation context
- `/admin` — admin-only status link

## Included

- Telegram webhook integration
- Gemini text responses
- Per-user rolling conversation context (latest 12 messages)
- SQLite user and message records
- Admin dashboard login
- User count and recent users
- Broadcast message form

## Important limitations

- This starter supports text chat only; it does not include image/voice/file input, payment/premium subscriptions, or advanced moderation.
- The SQLite path in the default Render config is `/tmp/synova.db`. On free/ephemeral hosting, local database data can be lost when the service restarts or redeploys. Use persistent storage or an external database if you need durable user records.
- Free hosting may sleep when idle. Always-on availability may require a paid hosting plan.
- Keep all API keys and bot tokens in Render Environment variables. Never commit them to GitHub.
