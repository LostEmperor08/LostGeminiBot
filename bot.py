import os
import threading
from flask import Flask
from telegram.ext import ApplicationBuilder, MessageHandler, filters
import google.generativeai as genai

# 1. Pella Heartbeat Server
app = Flask('')
@app.route('/')
def home():
    return "Bot is Online!"

def run_web():
    # Pella usually looks for a web server to mark it as 'Starting' success
    app.run(host='0.0.0.0', port=8080)

# 2. Gemini Bot Logic
async def handle_msg(update, context):
    genai.configure(api_key=os.getenv("GEMINI_KEY"))
    model = genai.GenerativeModel('gemini-1.5-flash')
    try:
        response = model.generate_content(update.message.text)
        await update.message.reply_text(response.text)
    except Exception as e:
        print(f"Error: {e}")

# 3. Execution
if __name__ == '__main__':
    # Start the web server in a background thread
    t = threading.Thread(target=run_web)
    t.start()
    
    # Start the Telegram Bot
    print("--- Starting Telegram Bot ---")
    token = os.getenv("TELEGRAM_TOKEN")
    bot_app = ApplicationBuilder().token(token).build()
    bot_app.add_handler(MessageHandler(filters.TEXT, handle_msg))
    bot_app.run_polling()
