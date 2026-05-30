import os
import requests
import telebot
from threading import Thread
from flask import Flask
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_KEY = os.getenv('GEMINI_API_KEY')

if not BOT_TOKEN or not GEMINI_KEY:
    raise ValueError("❌ BOT_TOKEN বা GEMINI_API_KEY পাওয়া যায়নি!")

bot = telebot.TeleBot(BOT_TOKEN, skip_pending=True)
app = Flask('')

@app.route('/')
def home():
    return "🤖 বট সার্ভার সচল আছে!"

def run():
    # Render-এর পোর্ট ইস্যু সমাধান করার জন্য
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()

def call_gemini(text_prompt):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{"parts": [{"text": text_prompt}]}]
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        if response.status_code == 200:
            return response.json()['candidates'][0]['content']['parts'][0]['text'].strip()
        else:
            return f"❌ গুগল সার্ভার এরর দিয়েছে (Code: {response.status_code})\nআপনার Gemini API Key-টি ড্যাশবোর্ডে আরেকবার চেক করুন।"
    except Exception as e:
        return f"❌ সংযোগ বিচ্ছিন্ন হয়েছে: {str(e)}"

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "🧠 সুপার ব্রেইন এআই সক্রিয় হয়েছে! এখন যেকোনো প্রশ্ন লিখে মেসেজ করুন।")

@bot.message_handler(func=lambda message: True)
def chat_handler(message):
    answer = call_gemini(message.text)
    bot.reply_to(message, answer)

if __name__ == "__main__":
    keep_alive()  # ফ্লাস্ক ওয়েব সার্ভার ব্যাকগ্রাউন্ডে চালু হবে
    print("🤖 Bot is starting...")
    bot.infinity_polling(timeout=60, long_polling_timeout=5, skip_pending=True)
                                 
