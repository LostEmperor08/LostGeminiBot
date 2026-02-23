import os, json, time, asyncio, warnings, sys
from datetime import datetime, timedelta

# Official SDKs
from openai import AsyncOpenAI
from mistralai import Mistral
import google.generativeai as genai
from telegram import Update, Poll, constants
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, JobQueue, PollAnswerHandler

warnings.filterwarnings("ignore", category=FutureWarning)

# --- CONFIG ---
OWNER_ID = 5917459734
OWNER_USERNAME = "@lostemperor_08"
BOT_TOKEN = "8245043931:AAF6pbRn30egtEEAffxUtDt1UbHxdv8pGoY"
OPENAI_KEY = "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"
GEMINI_KEY = "AIzaSyDJmngbKPCMd31cmuCv44oPy1aVwPgSyus"
MISTRAL_KEY = "Ne0sG0ECaY3LTIpIXgYNrTwkotCkg2oL"

# SDK Clients
openai_client = AsyncOpenAI(api_key=OPENAI_KEY)
mistral_client = Mistral(api_key=MISTRAL_KEY)
genai.configure(api_key=GEMINI_KEY)
gemini_model = genai.GenerativeModel('gemini-1.5-flash')

# Persistence
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)
FILES = {k: f"{DATA_DIR}/{k}.json" for k in ["vips", "users", "timers", "leaderboard", "settings"]}

def load_db(key, default):
    if os.path.exists(FILES[key]):
        with open(FILES[key], 'r') as f: return json.load(f)
    return default

def save_db(key, data):
    with open(FILES[key], 'w') as f: json.dump(data, f, indent=4)

vips = load_db("vips", [])
user_data = load_db("users", {})
timers = load_db("timers", {})
leaderboard = load_db("leaderboard", {}) # {uid: {"score": 0, "name": ""}}
settings = load_db("settings", {"quiz_active": False})
START_TIME = time.time()
user_cooldowns = {}

# --- AI ENGINE HUB ---
async def get_ai_response(prompt):
    # 1. OpenAI
    try:
        res = await openai_client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}], timeout=12)
        return res.choices[0].message.content, "OpenAI"
    except: pass
    # 2. Gemini
    try:
        res = gemini_model.generate_content(prompt)
        return res.text, "Gemini"
    except: pass
    # 3. Mistral
    try:
        res = await mistral_client.chat.complete_async(model="open-mistral-7b", messages=[{"role": "user", "content": prompt}])
        return res.choices[0].message.content, "Mistral"
    except: return "⚠️ All AI systems failed.", "None"

# --- CORE LOGIC ---
def check_credits(uid):
    uid_str = str(uid)
    today = datetime.now().strftime("%Y-%m-%d")
    if uid_str not in user_data or user_data[uid_str].get("reset") != today:
        user_data[uid_str] = {"daily": 0, "bonus": user_data.get(uid_str, {}).get("bonus", 0), "reset": today}
    return user_data[uid_str]

# --- HANDLERS ---
async def ai_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid in user_cooldowns and time.time() - user_cooldowns[uid] < 5:
        return await update.message.reply_text("⏳ Cooldown: 5s")
    
    u = check_credits(uid)
    limit = 25 if uid in vips else 2
    if uid != OWNER_ID and u["daily"] >= limit and u["bonus"] <= 0:
        return await update.message.reply_text("🪫 No credits! Correct quiz answers give +1 bonus.")

    query = " ".join(context.args)
    if not query: return await update.message.reply_text("❓ Usage: /ai [topic]")
    
    m = await update.message.reply_text("🔎 **Consulting AI Engines...**", parse_mode="Markdown")
    res, engine = await get_ai_response(query)
    user_cooldowns[uid] = time.time()
    
    if uid != OWNER_ID:
        if u["daily"] < limit: u["daily"] += 1
        else: u["bonus"] -= 1
        save_db("users", user_data)

    rem = "∞" if uid == OWNER_ID else (limit - u["daily"] + u["bonus"])
    safe_res = res.replace("<", "&lt;").replace(">", "&gt;")
    await m.edit_text(f"🎓 <b>Tutor ({engine}):</b>\n\n{safe_res}\n\n🔋 <b>Credits Left:</b> {rem}", parse_mode="HTML")

# --- QUIZ SYSTEM ---
async def hourly_quiz(context: ContextTypes.DEFAULT_TYPE):
    if not settings["quiz_active"]: return
    subj = ["Physics", "Chemistry", "Mathematics", "Biology"][int(time.time()/3600)%4]
    prompt = f"Create 1 hard MCQ for {subj}. Format: Question|Opt0|Opt1|Opt2|Opt3|CorrectIdx(0-3). No other text."
    res, _ = await get_ai_response(prompt)
    try:
        p = res.split("|")
        poll = await context.bot.send_poll(context.job.chat_id, f"📚 {subj} Quiz: {p[0]}", p[1:5], type=Poll.QUIZ, correct_option_id=int(p[5]), is_anonymous=False)
        context.bot_data[poll.poll.id] = int(p[5]) # Store correct ID
    except: pass

async def poll_answer_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    answer = update.poll_answer
    uid = str(answer.user.id)
    correct_id = context.bot_data.get(answer.poll_id)
    
    if correct_id is not None and answer.option_ids[0] == correct_id:
        # Reward
        if uid not in leaderboard: leaderboard[uid] = {"score": 0, "n": answer.user.first_name}
        leaderboard[uid]["score"] += 1
        u = check_credits(answer.user.id)
        u["bonus"] += 1
        save_db("leaderboard", leaderboard); save_db("users", user_data)

# --- TRACKING ---
async def set_timer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        dt, name = context.args[0], " ".join(context.args[1:]).lower()
        datetime.strptime(dt, "%d-%m-%Y")
        timers[name] = dt; save_db("timers", timers)
        await update.message.reply_text(f"✅ Timer set: <b>{name.upper()}</b>", parse_mode="HTML")
    except: await update.message.reply_text("❌ Use: /timer DD-MM-YYYY Name")

async def get_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = " ".join(context.args).lower()
    if name in timers:
        days = (datetime.strptime(timers[name], "%d-%m-%Y") - datetime.now()).days + 1
        await update.message.reply_text(f"⏳ <b>{name.upper()}</b>: {max(0, days)} days left", parse_mode="HTML")
    else: await update.message.reply_text("❌ Not found.")

# --- MAIN ---
if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("ai", ai_cmd))
    app.add_handler(CommandHandler("timer", set_timer))
    app.add_handler(CommandHandler("gettime", get_time))
    app.add_handler(CommandHandler("onquiz", lambda u,c: (settings.update({"quiz_active":True}), save_db("settings", settings), c.job_queue.run_repeating(hourly_quiz, 3600, chat_id=u.effective_chat.id))))
    app.add_handler(PollAnswerHandler(poll_answer_handler))
    print("🚀 Master Bot Started")
    app.run_polling()
