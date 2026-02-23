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
from mistralai import Mistral

# ==============================
# ENV VARIABLES (Render Safe)
# ==============================

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")

OWNER_ID = 5917459734
OWNER_USERNAME = "@lostemperor_08"

# Render persistent disk path
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
mistral_client = Mistral(api_key=MISTRAL_API_KEY)

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
# AI ENGINE (Auto Fallback)
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

def ask_mistral(prompt):
    try:
        response = mistral_client.chat.complete(
            model="mistral-small-latest",
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content
    except Exception:
        return None

def ask_ai(prompt):
    for provider in [ask_openai, ask_gemini, ask_mistral]:
        reply = provider(prompt)
        if reply:
            return reply
    return "⚠ All AI providers are temporarily unavailable."

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

def is_vip(uid):
    vip = load_json(VIP_FILE, [])
    return str(uid) in vip

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
/help

Owner:
/addvip user_id
/removevip user_id
/status"""
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

    if uid != OWNER_ID:
        total = user["credits"] + user["bonus"]
        if total <= 0:
            await update.message.reply_text("❌ No credits left.")
            return

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
# QUIZ SYSTEM
# ==============================

QUIZ_SUBJECTS = ["Physics", "Chemistry", "Mathematics", "Biology"]
quiz_active = False
quiz_index = 0

async def send_quiz(context: ContextTypes.DEFAULT_TYPE):
    global quiz_index
    if not quiz_active:
        return

    subject = QUIZ_SUBJECTS[quiz_index % 4]
    quiz_index += 1

    question = f"{subject}: 5 × 3 = ?"
    options = ["10", "15", "20", "25"]

    message = await context.bot.send_poll(
        chat_id=context.job.chat_id,
        question=question,
        options=options,
        type=Poll.QUIZ,
        correct_option_id=1,
        is_anonymous=False,
    )

    context.bot_data[message.poll.id] = {"correct": 1}

async def onquiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global quiz_active
    quiz_active = True
    chat_id = update.effective_chat.id
    context.job_queue.run_repeating(send_quiz, 3600, first=5, chat_id=chat_id)
    await update.message.reply_text("✅ Hourly quiz started.")

async def offquiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global quiz_active
    quiz_active = False
    context.job_queue.stop()
    await update.message.reply_text("❌ Quiz stopped.")

async def handle_poll(update: Update, context: ContextTypes.DEFAULT_TYPE):
    answer = update.poll_answer
    poll_id = answer.poll_id

    if poll_id in context.bot_data:
        correct = context.bot_data[poll_id]["correct"]
        if answer.option_ids[0] == correct:
            uid = answer.user.id
            user = get_user(uid)
            user["bonus"] += 1
            update_user(uid, user)

            board = load_json(LEADERBOARD_FILE, {})
            board[str(uid)] = board.get(str(uid), 0) + 1
            save_json(LEADERBOARD_FILE, board)

# ==============================
# LEADERBOARD
# ==============================

async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    board = load_json(LEADERBOARD_FILE, {})
    sorted_board = sorted(board.items(), key=lambda x: x[1], reverse=True)[:10]

    text = "🏆 Leaderboard\n\n"
    for i, (uid, score) in enumerate(sorted_board, 1):
        text += f"{i}. {uid} - {score}\n"

    await update.message.reply_text(text)

# ==============================
# PING & STATUS
# ==============================

async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uptime = int(time.time() - START_TIME)
    await update.message.reply_text(f"🏓 Uptime: {uptime} sec")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    await update.message.reply_text("🟢 Bot running normally.")

# ==============================
# VIP
# ==============================

async def addvip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    uid = context.args[0]
    vip = load_json(VIP_FILE, [])
    if uid not in vip:
        vip.append(uid)
        save_json(VIP_FILE, vip)
    await update.message.reply_text("VIP added.")

async def removevip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    uid = context.args[0]
    vip = load_json(VIP_FILE, [])
    if uid in vip:
        vip.remove(uid)
        save_json(VIP_FILE, vip)
    await update.message.reply_text("VIP removed.")

# ==============================
# MAIN
# ==============================

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("ai", ai_cmd))
    app.add_handler(CommandHandler("leaderboard", leaderboard))
    app.add_handler(CommandHandler("onquiz", onquiz))
    app.add_handler(CommandHandler("offquiz", offquiz))
    app.add_handler(CommandHandler("ping", ping))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("addvip", addvip))
    app.add_handler(CommandHandler("removevip", removevip))
    app.add_handler(MessageHandler(filters.POLL_ANSWER, handle_poll))

    print("Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
