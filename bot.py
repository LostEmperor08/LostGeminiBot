import os
import threading
from flask import Flask
from telegram.ext import ApplicationBuilder, MessageHandler, filters
import google.generativeai as genai

# 1. Web server for Koyeb health checks
app = Flask(__name__)
@app.route('/')
def health_check():
    return "Bot is alive", 200

def run_flask():
    app.run(host='0.0.0.0', port=8000)

# 2. Telegram Bot Logic
async def handle_message(update, context):
    genai.configure(api_key=os.getenv("GEMINI_KEY"))
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content(update.message.text)
    await update.message.reply_text(response.text)

def main():
    # Start Web Server in background
    threading.Thread(target=run_flask, daemon=True).start()
    
    # Start Telegram Bot
    token = os.getenv("TELEGRAM_TOKEN")
    application = ApplicationBuilder().token(token).build()
    application.add_handler(MessageHandler(filters.TEXT, handle_message))
    application.run_polling()

if __name__ == '__main__':
    main()
