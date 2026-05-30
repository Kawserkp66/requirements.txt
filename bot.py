import os
import sqlite3
import base64
import requests
from threading import Thread
from datetime import datetime
from flask import Flask
import telebot
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_KEY = os.getenv('GEMINI_API_KEY')

if not BOT_TOKEN or not GEMINI_KEY:
    raise ValueError("❌ BOT_TOKEN অথবা GEMINI_API_KEY খুঁজে পাওয়া যায়নি!")

bot = telebot.TeleBot(BOT_TOKEN, skip_pending=True)
app = Flask('')
DB_FILE = "bot_knowledge.db"

# 🧠 টু-দ্য-পয়েন্ট সিস্টেম নির্দেশিকা (ChatGPT / Gemini Standard)
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
    return "🤖 টোকেন সাপোর্টেড জেমিনি এআই সচল!"

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

# ========== API Engines (Token Compatibility Mode) ==========

def query_gemini_api(payload):
    """টোকেন এবং এপিআই কী উভয়ের জন্যই কম্প্যাটিবল রিকোয়েস্ট মেথড"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
    
    # টোকেন যদি AQ দিয়ে শুরু হয়, তবে গুগলের রিকোয়েস্টে বিয়ারার হেডার বা প্যারামিটার হিসেবে হ্যান্ডেল করা
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {GEMINI_KEY}" if GEMINI_KEY.startswith("AQ") else ""
    }
    
    # যদি সাধারণ API Key হয় তবে লিংকের সাথে যুক্ত হবে
    target_url = url if GEMINI_KEY.startswith("AQ") else f"{url}?key={GEMINI_KEY}"
    
    response = requests.post(target_url, headers=headers, json=payload, timeout=20)
    if response.status_code == 200:
        return response.json()['candidates'][0]['content']['parts'][0]['text'].strip()
    return None

# ========== Telegram Handlers ==========

@bot.message_handler(commands=['start'])
def start(message):
    welcome = "🧠 *সুপার ব্রেইন এআই সক্রিয়!*\n\n• যেকোনো ভাষায় প্রশ্ন করতে পারেন।\n• যেকোনো ছবি আপলোড করে তার বিবরণ বা সমাধান জানতে পারেন।"
    bot.reply_to(message, welcome, parse_mode="Markdown")

# ১. ইমেজ হ্যান্ডলার (ছবি অ্যানালাইসিস)
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
            }],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 400
            }
        }
        
        answer = query_gemini_api(payload)
        
        if answer:
            bot.delete_message(message.chat.id, status_msg.message_id)
            bot.reply_to(message, f"{answer}\n\n✨ _[Model: Gemini 1.5 Flash]_")
        else:
            bot.edit_message_text("❌ ক্লাউড এপিআই কোনো রেসপন্স করেনি। দয়া করে টোকেনটি পুনরায় চেক করুন।", message.chat.id, status_msg.message_id)
            
    except Exception as e:
        bot.reply_to(message, "❌ ছবি প্রসেস করার সময় কোনো সমস্যা হয়েছে।")

# ২. টেক্সট হ্যান্ডলার
@bot.message_handler(func=lambda message: True)
def chat_handler(message):
    user_id = message.chat.id
    user_text = message.text.strip()

    chat_context = get_chat_context(user_id)
    full_prompt = f"{AI_PERSONA}\n\n[Chat Context]:\n{chat_context}\n\nUser Question: {user_text}"
    
    payload = {
        "contents": [{"parts": [{"text": full_prompt}]}],
        "generationConfig": {
            "temperature": 0.2,
            "max_output_tokens": 350
        }
    }
    
    try:
        answer = query_gemini_api(payload)
        
        if answer:
            save_chat_memory(user_id, "User", user_text)
            save_chat_memory(user_id, "AI", answer)
            
            try:
                bot.reply_to(message, f"{answer}\n\n✨ _[Model: Gemini 1.5 Flash]_", parse_mode="Markdown")
            except:
                bot.reply_to(message, f"{answer}\n\n✨ _[Model: Gemini 1.5 Flash]_")
        else:
            bot.reply_to(message, "❌ ক্লাউড সার্ভার সংযোগ মডিউল সাড়া দিচ্ছে না। আপনার দেওয়া কী/টোকেনটি রিসিভ হচ্ছে না।")
            
    except Exception as e:
        bot.reply_to(message, "❌ সংযোগ ব্যাহত হয়েছে।")

if __name__ == "__main__":
    keep_alive()
    print("✅ হাইব্রিড জেমিনি ইঞ্জিন সফলভাবে চালিত!")
    try:
        bot.infinity_polling(timeout=60, long_polling_timeout=5, skip_pending=True)
    except Exception as e:
        print(f"❌ Polling Error: {e}")
  
