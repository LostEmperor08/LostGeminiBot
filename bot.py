import os
import json
import time
from datetime import datetime

from telegram import Update, Poll
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# AI SDKs
from openai import OpenAI
from google import genai

# ==============================
# ENV VARIABLES
# ==============================

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

OWNER_ID = 5917459734
OWNER_USERNAME = "@lostemperor_08"

DATA_FOLDER = "/opt/render/project/src/data"
os.makedirs(DATA_FOLDER, exist_ok=True)

USERS_FILE = f"{DATA_FOLDER}/users.json"
VIP_FILE = f"{DATA_FOLDER}/vip.json"
LEADERBOARD_FILE = f"{DATA_FOLDER}/leaderboard.json"

COOLDOWN_SECONDS = 5
START_TIME = time.time()

# ==============================
# AI CLIENTS
# ==============================

openai_client = OpenAI(api_key=OPENAI_API_KEY)
gemini_client = genai.Client(api_key=GEMINI_API_KEY)

# ==============================
# JSON UTILS
# ==============================

def load_json(file, default):
    if not os.path.exists(file):
        with open(file, "w") as f:
            json.dump(default, f)
    with open(file, "r") as f:
        return json.load(f)

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=4)

# ==============================
# AI ENGINE
# ==============================

def ask_openai(prompt):
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content
    except Exception:
        return None

def ask_gemini(prompt):
    try:
        response = gemini_client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt,
        )
        return response.text
    except Exception:
        return None

def ask_ai(prompt):
    reply = ask_openai(prompt)
    if reply:
        return reply

    reply = ask_gemini(prompt)
    if reply:
        return reply

    return "⚠ AI services temporarily unavailable."

# ==============================
# CREDIT SYSTEM
# ==============================

def reset_daily():
    users = load_json(USERS_FILE, {})
    today = datetime.now().strftime("%Y-%m-%d")

    for uid in users:
        if users[uid]["last_reset"] != today:
            users[uid]["credits"] = 2
            users[uid]["bonus"] = 0
            users[uid]["last_reset"] = today

    save_json(USERS_FILE, users)

def get_user(uid):
    users = load_json(USERS_FILE, {})
    today = datetime.now().strftime("%Y-%m-%d")

    if str(uid) not in users:
        users[str(uid)] = {
            "credits": 2,
            "bonus": 0,
            "last_reset": today,
            "cooldown": 0
        }
        save_json(USERS_FILE, users)

    return users[str(uid)]

def update_user(uid, data):
    users = load_json(USERS_FILE, {})
    users[str(uid)] = data
    save_json(USERS_FILE, users)

# ==============================
# COMMANDS
# ==============================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"📚 Study Bot Active\nOwner: {OWNER_USERNAME}\nUse /help"
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        """📘 Commands

/ai [question]
/leaderboard
/onquiz
/offquiz
/ping
/help"""
    )

# ==============================
# AI COMMAND
# ==============================

async def ai_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    reset_daily()
    user = get_user(uid)

    now = time.time()
    if now - user["cooldown"] < COOLDOWN_SECONDS:
        await update.message.reply_text("⏳ Wait 5 seconds.")
        return

    total = user["credits"] + user["bonus"]
    if uid != OWNER_ID and total <= 0:
        await update.message.reply_text("❌ No credits left.")
        return

    if uid != OWNER_ID:
        if user["bonus"] > 0:
            user["bonus"] -= 1
        else:
            user["credits"] -= 1

    user["cooldown"] = now
    update_user(uid, user)

    query = " ".join(context.args)
    if not query:
        await update.message.reply_text("Provide a question.")
        return

    reply = ask_ai(query)
    remaining = user["credits"] + user["bonus"]

    await update.message.reply_text(
        f"{reply}\n\n💳 Credits left: {remaining}"
    )

# ==============================
# PING
# ==============================

async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uptime = int(time.time() - START_TIME)
    await update.message.reply_text(f"🏓 Uptime: {uptime} sec")

# ==============================
# MAIN
# ==============================

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("ai", ai_cmd))
    app.add_handler(CommandHandler("ping", ping))

    print("Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
