# ✦ SYNOVA AI — Telegram AI Chatbot

A Telegram AI chatbot powered by the Gemini API, with a responsive web landing page and password-protected admin dashboard.

## Features
- AI conversations with short rolling context
- `/start`, `/help`, `/new`, `/admin`
- SQLite user and conversation storage
- Admin dashboard with usage stats and user list
- Admin broadcast messages
- Telegram webhook for Render deployment
- Mobile-friendly landing page

## 1. Create your Telegram bot
1. Open Telegram and message **@BotFather**.
2. Send `/newbot`, choose the name `SYNOVA AI` and a unique username.
3. Copy the bot token. Keep it private.

## 2. Get a Gemini API key
1. Visit https://aistudio.google.com/app/apikey
2. Create an API key and copy it.
3. Do not share the key publicly or commit it to GitHub.

## 3. Find your Telegram numeric user ID
Message **@userinfobot** or another trusted ID bot and copy your numeric ID. Put it in `ADMIN_ID`.

## 4. Upload to GitHub
1. Create a new GitHub repository named `SYNOVA-AI`.
2. Upload all files and folders from this project.
3. Make sure `app/main.py`, `requirements.txt`, and `render.yaml` are at the repository root structure shown here.
4. Never upload `.env` or API keys.

## 5. Deploy on Render
1. Sign in at https://render.com and choose **New + → Blueprint**.
2. Connect your GitHub account and select the `SYNOVA-AI` repository.
3. Render reads `render.yaml`. Enter the requested secret values:
   - `BOT_TOKEN`
   - `GEMINI_API_KEY`
   - `ADMIN_ID`
   - `ADMIN_PASSWORD`
4. Deploy and wait for the service to become **Live**.
5. Open the Render service URL. The landing page should show SYNOVA AI.
6. Open `https://YOUR-RENDER-URL/admin` to sign in to the admin panel.

## 6. Admin commands
- Telegram `/admin` — bot usage stats (only the configured ADMIN_ID)
- Web `/admin` — dashboard, user list, broadcast form
- `/new` — clears the user's saved chat context

## Important notes
- Keep bot and Gemini keys secret. If a token is exposed, revoke it through BotFather / Google AI Studio and replace it in Render environment variables.
- Free hosting may sleep or have usage limits depending on Render's current plan. A sleeping service may take time to wake up. For always-on operation, use a suitable paid Render instance.
- This starter Blueprint uses `/tmp` so it can deploy on a free web service, but `/tmp` is temporary: users and chat history can be lost when the service restarts or redeploys. For persistent data, use a paid Render service with a persistent disk (change `DATABASE_PATH` to `/var/data/synova.db` and add a disk mounted at `/var/data`) or migrate the app to a managed database.
- Gemini API quotas, rate limits, and model availability depend on your Google AI Studio account and current Google policies. If the default model is unavailable, change `GEMINI_MODEL` in Render environment variables to a model enabled for your API key.
- This starter project supports text chats. Image, voice, file upload, payments, and per-user premium plans are not included yet.
- The admin broadcast sends a message to every registered bot user. Use it responsibly and only for relevant announcements.
