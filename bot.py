import os
import base64
import requests
from threading import Thread
import telebot
from dotenv import load_dotenv
from flask import Flask

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_KEY = os.getenv('GEMINI_API_KEY')

if not BOT_TOKEN or not GEMINI_KEY:
    raise ValueError("❌ BOT_TOKEN অথবা GEMINI_API_KEY খুঁজে পাওয়া যায়নি!")

bot = telebot.TeleBot(BOT_TOKEN, skip_pending=True)
app = Flask('')

@app.route('/')
def home():
    return "🤖 বট সার্ভার সচল আছে!"

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()

def call_gemini(payload):
    # আপনার টোকেন বা এপিআই কী সরাসরি লিংক করার ইউআরএল
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=20)
        if response.status_code == 200:
            return response.json()['candidates'][0]['content']['parts'][0]['text'].strip()
        return f"❌ গুগল সার্ভার এরর দিয়েছে (Code: {response.status_code})"
    except Exception as e:
        return f"❌ সংযোগের সময় সমস্যা হয়েছে: {str(e)}"

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "🧠 এআই বট সক্রিয় হয়েছে! এখন যেকোনো প্রশ্ন করতে পারেন।")

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    try:
        status = bot.reply_to(message, "🔍 ছবি বিশ্লেষণ করা হচ্ছে...")
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        img_b64 = base64.b64encode(downloaded_file).decode('utf-8')
        
        caption = message.caption if message.caption else "Analyze this image briefly."
        
        payload = {
            "contents": [{
                "parts": [
                    {"text": caption},
                    {"inlineData": {"mimeType": "image/jpeg", "data": img_b64}}
                ]
            }]
        }
        answer = call_gemini(payload)
        bot.delete_message(message.chat.id, status.message_id)
        bot.reply_to(message, answer)
    except Exception as e:
        bot.reply_to(message, "❌ ছবি প্রসেস করা যায়নি।")

@bot.message_handler(func=lambda message: True)
def chat_handler(message):
    payload = {
        "contents": [{"parts": [{"text": message.text}]}]
    }
    answer = call_gemini(payload)
    bot.reply_to(message, answer)

if __name__ == "__main__":
    keep_alive()
    print("🤖 Bot is starting...")
    bot.infinity_polling(timeout=60, long_polling_timeout=5, skip_pending=True)
                                    
