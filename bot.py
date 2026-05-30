import os
import sqlite3
import base64
import requests
from threading import Thread
from datetime import datetime
from flask import Flask
import telebot
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_KEY = os.getenv('GEMINI_API_KEY')

if not BOT_TOKEN or not GEMINI_KEY:
    raise ValueError("❌ BOT_TOKEN অথবা GEMINI_API_KEY খুঁজে পাওয়া যায়নি!")

bot = telebot.TeleBot(BOT_TOKEN, skip_pending=True)
app = Flask('')
DB_FILE = "bot_knowledge.db"

AI_PERSONA = (
    "You are an advanced AI assistant, trained to be highly helpful, accurate, and concise. "
    "তুমি ব্যবহারকারীর প্রশ্ন বা আপলোড করা ছবির গভীর অ্যানালাইসিস করবে এবং অতিরিক্ত কোনো ভূমিকা বা অপ্রাসঙ্গিক কথা না বলে সরাসরি মূল উত্তর দেবে। "
    "উত্তর সবসময় যৌক্তিক, পয়েন্ট-ভিত্তিক এবং সংক্ষিপ্ত হতে হবে।"
)

def init_database():
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                role TEXT,
                content TEXT,
                timestamp TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"❌ Database Error: {e}")

init_database()

@app.route('/')
def home():
    return "🤖 টোকেন সাপোর্টেড জেমিনি এআই পুরোপুরি সচল!"

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()

# ========== Chat Memory ==========
def save_chat_memory(user_id, role, content):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO chat_history (user_id, role, content, timestamp)
            VALUES (?, ?, ?, ?)
        ''', (str(user_id), role, content, datetime.now()))
        conn.commit()
        cursor.execute('''
            DELETE FROM chat_history WHERE id NOT IN (
                SELECT id FROM chat_history WHERE user_id = ? ORDER BY timestamp DESC LIMIT 4
            ) AND user_id = ?
        ''', (str(user_id), str(user_id)))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Memory Save Error: {e}")

def get_chat_context(user_id):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT role, content FROM chat_history WHERE user_id = ? ORDER BY timestamp ASC", (str(user_id),))
        rows = cursor.fetchall()
        conn.close()
        context = ""
        for role, content in rows:
            context += f"{role}: {content}\n"
        return context
    except:
        return ""

# ========== API Gateway (Token Linker) ==========
def query_gemini_api(payload):
    # নতুন সিকিউরিটি টোকেন ডাইরেক্ট ইউআরএল এপিআই গেটওয়ে
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
    headers = {"Content-Type": "application/json"}
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=25)
        if response.status_code == 200:
            return response.json()['candidates'][0]['content']['parts'][0]['text'].strip()
        else:
            print(f"API Error Code: {response.status_code}, Response: {response.text}")
            return None
    except Exception as e:
        print(f"Request Error: {e}")
        return None

# ========== Telegram Handlers ==========
@bot.message_handler(commands=['start'])
def start(message):
    welcome = "🧠 *সুপার BRN এআই সক্রিয়!*\n\n• যেকোনো ভাষায় প্রশ্ন করতে পারেন।\n• যেকোনো ছবি আপলোড করে তার বিবরণ বা সমাধান জানতে পারেন।"
    bot.reply_to(message, welcome, parse_mode="Markdown")

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    try:
        status_msg = bot.reply_to(message, "🔍 ছবি বিশ্লেষণ করছি... একটু অপেক্ষা করুন।⏳")
        file_id = message.photo[-1].file_id
        file_info = bot.get_file(file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        image_base64 = base64.b64encode(downloaded_file).decode('utf-8')
        
        caption = message.caption.strip() if message.caption else "Analyze this image and explain concisely."
        full_prompt = f"{AI_PERSONA}\n\nUser Prompt: {caption}"
        
        payload = {
            "contents": [{
                "parts": [
                    {"text": full_prompt},
                    {
                        "inlineData": {
                            "mimeType": "image/jpeg",
                            "data": image_base64
                        }
                    }
                ]
            }]
        }
        answer = query_gemini_api(payload)
        if answer:
            bot.delete_message(message.chat.id, status_msg.message_id)
            bot.reply_to(message, f"{answer}\n\n✨ _[Model: Gemini 1.5 Flash]_")
        else:
            bot.edit_message_text("❌ ক্লাউড সার্ভার রেসপন্স করেনি। আপনার টোকেনটির মেয়াদ শেষ হয়েছে, দয়া করে নতুন টোকেন জেনারেট করে বসান।", message.chat.id, status_msg.message_id)
    except Exception as e:
        bot.reply_to(message, "❌ ছবি প্রসেস করতে ব্যর্থ হয়েছে।")

@bot.message_handler(func=lambda message: True)
def chat_handler(message):
    user_id = message.chat.id
    user_text = message.text.strip()
    chat_context = get_chat_context(user_id)
    full_prompt = f"{AI_PERSONA}\n\n[Chat Context]:\n{chat_context}\n\nUser Question: {user_text}"
    
    payload = {
        "contents": [{"parts": [{"text": full_prompt}]}]
    }
    try:
        answer = query_gemini_api(payload)
        if answer:
            save_chat_memory(user_id, "User", user_text)
            save_chat_memory(user_id, "AI", answer)
            bot.reply_to(message, f"{answer}\n\n✨ _[Model: Gemini 1.5 Flash]_")
        else:
            bot.reply_to(message, "❌ ক্লাউড এপিআই রেসপন্স করছে না। আপনার জেমিনি কী/টোকেনটি রি-চেক করুন।")
    except Exception as e:
        bot.reply_to(message, "❌ কানেকশন এরর।")

if __name__ == "__main__":
    keep_alive()
    print("✅ হাইব্রিড টোকেন ইঞ্জিন সফলভাবে চালিত!")
    try:
        bot.infinity_polling(timeout=60, long_polling_timeout=5, skip_pending=True)
    except Exception as e:
        print(f"❌ Polling Error: {e}")

