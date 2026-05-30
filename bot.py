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

# এআই টুলস এবং ফ্রি ওয়েবসাইটের স্মার্ট ডেটাবেজ ডিকশনারি
SPECIAL_TOOLS_LINKS = {
    "ভিডিও": "🎬 *ফ্রি ভিডিও এডিটিং ও ডাবিং এআই সাইটসমূহ:*\n1. [ElevenLabs Video Dubbing](https://elevenlabs.io/dubbing) - অডিও ও ভাষা পরিবর্তনের জন্য সেরা।\n2. [Dubverse AI](https://dubverse.ai/) - ফ্রি ভিডিও ডাবিং প্ল্যাটফর্ম।\n3. [CapCut Web](https://www.capcut.com/) - আনলিমিটেড ফ্রি ভিডিও এডিটিং।",
    "ভাষা": "🗣️ *ভাষা পরিবর্তন ও ডাবিং এআই সাইটসমূহ:*\n1. [Rask AI](https://www.rask.ai/) - ভিডিওর ভাষা পরিবর্তন ও লিপ-সিঙ্ক।\n2. [Hugging Face Seamless](https://huggingface.co/spaces) - ওপেন সোর্স ফ্রি ট্রান্সলেটর।",
    "ছবি": "🎨 *ফ্রি ছবি ও গ্রাফিক্স তৈরির এআই সাইটসমূহ:*\n1. [Pollinations AI](https://pollinations.ai/) - আনলিমিটেড ফ্রি ইমেজ জেনারেশন।\n2. [Bing Image Creator](https://www.bing.com/images/create) - হাই কোয়ালিটি ডল-ই ৩ ছবি।\n3. [Canva Free](https://www.canva.com/) - সেরা গ্রাফিক ডিজাইনিং টুল।",
    "গ্রাফিক": "📐 *ফ্রি গ্রাফিক ডিজাইন এআই সাইটসমূহ:*\n1. [Canva AI](https://www.canva.com/) - এআই চালিত গ্রাফিক্স টেমপ্লেট।\n2. [Adobe Express](https://www.adobe.com/express/) - প্রফেশনাল ফ্রি ডিজাইনিং টুল।",
    "গান": "🎵 *ফ্রি গান ও মিউজিক তৈরির এআই সাইটসমূহ:*\n1. [Suno AI](https://suno.com/) - যেকোনো টেক্সট থেকে চমৎকার গান ও সুর তৈরি।\n2. [Udio AI](https://www.udio.com/) - প্রফেশনাল এআই মিউজিক জেনারেটর।",
    "গেম": "🎮 *ফ্রি গেম মেকিং ও কোডিং এআই সাইটসমূহ:*\n1. [Rosebud AI](https://www.rosebud.ai/) - টেক্সট লিখে এআই দিয়ে গেম তৈরি।\n2. [Hugging Face Games](https://huggingface.co/spaces) - ওপেন সোর্স ওয়েব গেম মেকার।",
    "থ্রিডি": "🧊 *ফ্রি ৩ডি (3D) ছবি ও ভিডিও তৈরির এআই সাইটসমূহ:*\n1. [Luma Dream Machine](https://lumalabs.ai/dream-machine) - হাই কোয়ালিটি ৩ডি ভিডিও ও অ্যানিমেশন।\n2. [Spline 3D](https://spline.design/) - ফ্রি ওয়েব ৩ডি ডিজাইন টুল।\n3. [Tripo 3D](https://www.tripo3d.ai/) - টেক্সট থেকে ঝটপট ৩ডি মডেল তৈরি।"
}

# এআই ব্যক্তিত্ব নির্দেশিকা (System Prompt)
AI_PERSONA = "তুমি একজন অত্যন্ত বুদ্ধিমান, দূরदर्शी এবং বন্ধুসুলভ অল-রাউন্ডার এআই অ্যাসিস্ট্যান্ট। তোমার নাম 'সুপার ব্রেইন এআই'। মানুষের যেকোনো সমস্যার সমাধান তুমি খুব সহজ ভাষায়, সুন্দর ইমোজি ব্যবহার করে বুঝিয়ে দাও।"

def init_database():
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS knowledge (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question TEXT UNIQUE,
                answer TEXT,
                source TEXT,
                learned_date TIMESTAMP
            )
        ''')
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
                SELECT id FROM chat_history WHERE user_id = ? ORDER BY timestamp DESC LIMIT 10
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

# ========== এআই ইঞ্জিন ==========

def query_gemini(question, context=""):
    try:
        config = AI_PROVIDERS["gemini"]
        if not config["enabled"]: return None
        headers = {"Content-Type": "application/json"}
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

def find_relevant_links(user_text):
    suggested_links = ""
    for keyword, link_info in SPECIAL_TOOLS_LINKS.items():
        if keyword in user_text.lower() or keyword in user_text:
            suggested_links += link_info + "\n\n"
    return suggested_links

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

    chat_context = get_chat_context(user_id)

    answer = query_gemini(user_text, chat_context)
    source = "Google Gemini"

    if not answer:
        answer = query_groq(user_text, chat_context)
        source = "Groq (Llama 3.1)"

    # বিশেষ কাজের জন্য ফ্রি লিংক খোঁজা
    web_links = find_relevant_links(user_text)

    if answer:
        save_chat_memory(user_id, "User", user_text)
        save_chat_memory(user_id, "AI", answer)
        
        final_text = f"{answer}\n\n✨ _[উত্তর দিয়েছে: {source}]_\n\n"
        if web_links:
            final_text += f"🔗 *আপনার কাজের জন্য ফ্রি প্রফেশনাল এআই ওয়েবসাইট সমূহ:*\n\n{web_links}"
            
        try:
            bot.edit_message_text(final_text, message.chat.id, msg.message_id, parse_mode="Markdown", disable_web_page_preview=True)
        except:
            bot.edit_message_text(final_text, message.chat.id, msg.message_id)
    else:
        if web_links:
            bot.edit_message_text(f"🔗 *আপনার জন্য ফ্রি এআই ওয়েবসাইট লিংকসমূহ পাওয়া গেছে:*\n\n{web_links}", message.chat.id, msg.message_id, parse_mode="Markdown", disable_web_page_preview=True)
        else:
            bot.edit_message_text("❌ আমার ক্লাউড ব্রেইন এই মুহূর্তে সাড়া দিচ্ছে না। দয়া করে একটু পর আবার চেষ্টা করুন বন্ধু!", message.chat.id, msg.message_id)

if __name__ == "__main__":
    keep_alive()
    print("✅ মেমোরি-পাওয়ার্ড আলটিমেট এআই বট সফলভাবে চালিত!")
    try:
        bot.infinity_polling(timeout=60, long_polling_timeout=5, skip_pending=True)
    except Exception as e:
        print(f"❌ Polling Error: {e}")
      
