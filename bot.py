import os
import sqlite3
import requests
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

AI_PROVIDERS = {
    "gemini": {
        "name": "🌐 Google Gemini",
        "url": f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={os.getenv('GEMINI_API_KEY')}",
        "enabled": os.getenv("GEMINI_API_KEY") is not None,
    },
    "groq": {
        "name": "⚡ Groq (Llama 3.1)",
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "enabled": os.getenv("GROQ_API_KEY") is not None,
        "key": os.getenv("GROQ_API_KEY"),
        "model": "llama-3.1-8b-instant"
    }
}

# এআই ব্যক্তিত্ব নির্দেশিকা (System Prompt)
AI_PERSONA = "তুমি একজন অত্যন্ত বুদ্ধিমান, দূরদর্শী এবং বন্ধুসুলভ অল-রাউন্ডার এআই অ্যাসিস্ট্যান্ট। তোমার নাম 'সুপার ব্রেইন এআই'। মানুষের যেকোনো সমস্যার সমাধান তুমি খুব সহজ ভাষায়, সুন্দর ইমোজি ব্যবহার করে বুঝিয়ে দাও।"

def init_database():
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        # গ্লোবাল নলেজ টেবিল
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS knowledge (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question TEXT UNIQUE,
                answer TEXT,
                source TEXT,
                learned_date TIMESTAMP
            )
        ''')
        # মেমোরি/চ্যাট হিস্ট্রি টেবিল (নতুন যুক্ত করা হয়েছে)
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
    return "🤖 মেমোরি ও পারসোনালিটি সমৃদ্ধ সুপার এআই সচল!"

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()

# ========== স্মৃতিশক্তি (Chat Memory) হ্যান্ডলার ফাংশনস ==========

def save_chat_memory(user_id, role, content):
    """ব্যবহারকারী এবং এআই-এর কথা ডেটাবেজে সেভ রাখা"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO chat_history (user_id, role, content, timestamp)
            VALUES (?, ?, ?, ?)
        ''', (str(user_id), role, content, datetime.now()))
        conn.commit()
        
        # মেমোরি ক্লিনআপ: প্রতি ইউজারের শুধু শেষ ১০টি মেসেজ রাখবে যাতে ডেটাবেজ ভারী না হয়
        cursor.execute('''
            DELETE FROM chat_history WHERE id NOT IN (
                SELECT id FROM chat_history WHERE user_id = ? ORDER BY timestamp DESC LIMIT 10
            ) AND user_id = ?
        ''', (str(user_id), str(user_id)))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Memory Save Error: {e}")

def get_chat_context(user_id):
    """আগের চ্যাটের প্রসঙ্গ বা হিস্ট্রি উদ্ধার করা"""
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

# ========== এআই ইঞ্জিন (স্মার্ট প্রম্পটিং সহ) ==========

def query_gemini(question, context=""):
    try:
        config = AI_PROVIDERS["gemini"]
        if not config["enabled"]: return None
        headers = {"Content-Type": "application/json"}
        
        # ব্যক্তিত্ব এবং আগের স্মৃতি একসাথে প্রম্পটে পাঠানো হচ্ছে
        full_prompt = f"{AI_PERSONA}\n\n[আগের চ্যাট মেমোরি]:\n{context}\n\n[ইউজারের বর্তমান প্রশ্ন]: {question}"
        
        payload = {"contents": [{"parts": [{"text": full_prompt}]}]}
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
        
        full_prompt = f"{AI_PERSONA}\n\n[আগের চ্যাট মেমোরি]:\n{context}\n\n[ইউজারের বর্তমান প্রশ্ন]: {question}"
        
        payload = {
            "model": config["model"],
            "messages": [{"role": "user", "content": full_prompt}],
            "temperature": 0.7, "max_completion_tokens": 400
        }
        response = requests.post(config["url"], headers=headers, json=payload, timeout=12)
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content'].strip()
    except: pass
    return None

# ========== চ্যাট হ্যান্ডলার ==========

@bot.message_handler(commands=['start'])
def start(message):
    welcome = """
🧠 *স্বাগতম! আমি এখন 'সুপার ব্রেইন এআই' হিসেবে আপগ্রেড হয়েছি!*

আমার ভেতরের কমতিগুলো দূর করে আমাকে দেওয়া হয়েছে:
🌟 *স্মৃতিশক্তি (Real Memory):* আমি এখন আপনার আগের কথা মনে রাখতে পারি!
🎭 *আসল ব্যক্তিত্ব (AI Persona):* আমি এখন আরও বন্ধুসুলভ ও নিখুঁত।
🛡️ *সার্ভার সেফটি:* একটি এআই ডাউন থাকলে আরেকটি অটোমেটিক ব্যাকআপ দেবে।

💡 যেকোনো বিষয়ে কথা বলা শুরু করুন, আমাদের আগের কথা আমার মনে থাকবে!
    """
    bot.reply_to(message, welcome, parse_mode="Markdown")

@bot.message_handler(func=lambda message: True)
def chat_handler(message):
    user_id = message.chat.id
    user_text = message.text.strip()

    msg = bot.reply_to(message, "🧠 আগের কথা মনে করার চেষ্টা করছি এবং নেটওয়ার্ক স্ক্যান করছি... ⏳")

    # ১. ডেটাবেজ থেকে আগের চ্যাট হিস্ট্রি/কনটেক্সট তুলে আনা
    chat_context = get_chat_context(user_id)

    # ২. জেমিনি দিয়ে চেষ্টা করা (প্রথম চয়েস)
    answer = query_gemini(user_text, chat_context)
    source = "Google Gemini"

    # ৩. ফলব্যাক চেইন: জেমিনি ফেল করলে অটোমেটিক গ্রক (Groq) কাজ করবে
    if not answer:
        answer = query_groq(user_text, chat_context)
        source = "Groq (Llama 3.1)"

    if answer:
        # বর্তমান চ্যাটটি ভবিষ্যতে মনে রাখার জন্য মেমোরিতে সেভ করা
        save_chat_memory(user_id, "User", user_text)
        save_chat_memory(user_id, "AI", answer)
        
        final_text = f"{answer}\n\n✨ _[উত্তর দিয়েছে: {source}]_"
        try:
            bot.edit_message_text(final_text, message.chat.id, msg.message_id, parse_mode="Markdown")
        except:
            bot.edit_message_text(final_text, message.chat.id, msg.message_id)
    else:
        bot.edit_message_text("❌ আমার ক্লাউড ব্রেইন এই মুহূর্তে সাড়া দিচ্ছে না। দয়া করে একটু পর আবার চেষ্টা করুন বন্ধু!", message.chat.id, msg.message_id)

if __name__ == "__main__":
    print("✅ মেমোরি-পাওয়ার্ড আলটিমেট এআই বট সফলভাবে চালিত!")
    try:
        bot.infinity_polling(timeout=60, long_polling_timeout=5, skip_pending=True)
    except Exception as e:
        print(f"❌ Polling Error: {e}")
  
