import os
import sqlite3
import requests
import base64
from threading import Thread
from datetime import datetime
from flask import Flask
import telebot
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN environment variable এ খুঁজে পাওয়া যায়নি!")

bot = telebot.TeleBot(BOT_TOKEN, skip_pending=True)
app = Flask('')

DB_FILE = "bot_knowledge.db"
GEMINI_KEY = os.getenv('GEMINI_API_KEY')

AI_PROVIDERS = {
    "gemini": {
        "name": "🌐 Google Gemini",
        "url": f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}",
        "enabled": GEMINI_KEY is not None,
    },
    "groq": {
        "name": "⚡ Groq (Llama 3.1)",
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "enabled": os.getenv("GROQ_API_KEY") is not None,
        "key": os.getenv("GROQ_API_KEY"),
        "model": "llama-3.1-8b-instant"
    }
}

# 🧠 ChatGPT & Gemini Standard System Prompt
AI_PERSONA = (
    "You are an advanced AI assistant, trained to be highly helpful, accurate, and concise. "
    "তুমি ব্যবহারকারীর প্রশ্নের বা আপলোড করা ছবির গভীর অ্যানালাইসিস করবে এবং অতিরিক্ত কোনো ভূমিকা বা অপ্রাসঙ্গিক কথা না বলে সরাসরি মূল উত্তর দেবে। "
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
    return "🤖 ChatGPT (Text + Image) মোডে সুপার এআই সচল!"

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
                SELECT id FROM chat_history WHERE user_id = ? ORDER BY timestamp DESC LIMIT 5
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

# ========== AI Engines (Text & Vision Support) ==========

def query_gemini_vision(image_base64, caption=""):
    """ছবির তথ্য অ্যানালাইসিস করার জন্য জেমিনি ভিশন পে-লোড"""
    try:
        config = AI_PROVIDERS["gemini"]
        if not config["enabled"]: return None
        
        headers = {"Content-Type": "application/json"}
        prompt_text = f"{AI_PERSONA}\n\nUser Prompt: {caption if caption else 'Analyze this image and explain concisely.'}"
        
        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt_text},
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
        
        response = requests.post(config["url"], headers=headers, json=payload, timeout=20)
        if response.status_code == 200:
            return response.json()['candidates'][0]['content']['parts'][0]['text'].strip()
    except: pass
    return None

def query_gemini(question, context=""):
    try:
        config = AI_PROVIDERS["gemini"]
        if not config["enabled"]: return None
        
        headers = {"Content-Type": "application/json"}
        full_text = f"{AI_PERSONA}\n\n[Chat History]:\n{context}\n\nUser: {question}"
        
        payload = {
            "contents": [{"parts": [{"text": full_text}]}],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 300
            }
        }
        
        response = requests.post(config["url"], headers=headers, json=payload, timeout=12)
        if response.status_code == 200:
            return response.json()['candidates'][0]['content']['parts'][0]['text'].strip()
    except: pass
    return None

def query_groq(question, context=""):
    try:
        config = AI_PROVIDERS["groq"]
        if not config["enabled"] or not config["key"]: return None
        
        headers = {"Authorization": f"Bearer {config['key']}", "Content-Type": "application/json"}
        full_text = f"{AI_PERSONA}\n\n[Chat History]:\n{context}\n\nUser: {question}"
        
        payload = {
            "model": config["model"],
            "messages": [{"role": "user", "content": full_text}],
            "temperature": 0.2,
            "max_tokens": 300
        }
        
        response = requests.post(config["url"], headers=headers, json=payload, timeout=12)
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content'].strip()
    except: pass
    return None

# ========== Telegram Handlers ==========

@bot.message_handler(commands=['start'])
def start(message):
    welcome = "🤖 *সুপার ব্রেইন এআই (ChatGPT মোড) সক্রিয়!*\n\n• যেকোনো ভাষায় প্রশ্ন করতে পারেন।\n• যেকোনো ছবি আপলোড করে সেটির বিষয়ে জানতে চাইতে পারেন।"
    bot.reply_to(message, welcome, parse_mode="Markdown")

# ১. ছবি হ্যান্ডলার (Image / Photo Analyzer)
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    try:
        # টেলিগ্রাম থেকে ছবির ফাইল আইডি নেওয়া (সবচেয়ে হাই কোয়ালিটি ছবি)
        file_id = message.photo[-1].file_id
        file_info = bot.get_file(file_id)
        
        # ফাইলটি ডাউনলোড করা
        downloaded_file = bot.download_file(file_info.file_path)
        
        # ছবিটিকে Base64 ফরম্যাটে কনভার্ট করা
        image_base64 = base64.b64encode(downloaded_file).decode('utf-8')
        
        caption = message.caption.strip() if message.caption else ""
        
        status_msg = bot.reply_to(message, "🔍 ছবি বিশ্লেষণ করছি... একটু অপেক্ষা করুন।")
        
        # জেমিনি ভিশন দিয়ে ছবি স্ক্যান
        answer = query_gemini_vision(image_base64, caption)
        
        if answer:
            bot.delete_message(message.chat.id, status_msg.message_id)
            bot.reply_to(message, f"{answer}\n\n✨ _[Model: Google Gemini Vision]_")
        else:
            bot.edit_message_text("❌ দুঃখিত! এই মুহূর্তে ছবিটি স্ক্যান করা গেল না। দয়া করে নিশ্চিত করুন আপনার GEMINI_API_KEY সঠিকভাবে কাজ করছে কি না।", message.chat.id, status_msg.message_id)
    except Exception as e:
        bot.reply_to(message, "❌ ছবি প্রসেস করার সময় কোনো সমস্যা হয়েছে।")

# ২. টেক্সট মেসেজ হ্যান্ডলার
@bot.message_handler(func=lambda message: True)
def chat_handler(message):
    user_id = message.chat.id
    user_text = message.text.strip()

    chat_context = get_chat_context(user_id)
    
    answer = query_gemini(user_text, chat_context)
    source = "Google Gemini"

    if not answer:
        answer = query_groq(user_text, chat_context)
        source = "Groq (Llama 3.1)"

    if answer:
        save_chat_memory(user_id, "User", user_text)
        save_chat_memory(user_id, "AI", answer)
        
        final_text = f"{answer}\n\n✨ _[Model: {source}]_"
        try:
            bot.reply_to(message, final_text, parse_mode="Markdown")
        except:
            bot.reply_to(message, final_text)
    else:
        bot.reply_to(message, "❌ সিস্টেম সাময়িকভাবে সাড়া দিচ্ছে না।")

if __name__ == "__main__":
    keep_alive()
    print("✅ ChatGPT টেক্সট ও ভিশন মোডে বট সফলভাবে রান হয়েছে!")
    try:
        bot.infinity_polling(timeout=60, long_polling_timeout=5, skip_pending=True)
    except Exception as e:
        print(f"❌ Polling Error: {e}")
