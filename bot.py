import os
import json
import requests
from threading import Thread
from flask import Flask
import telebot
from dotenv import load_dotenv
from datetime import datetime
import sqlite3

# Load environment variables
load_dotenv()

# Get Bot Token only
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN not found in environment variables!")

bot = telebot.TeleBot(BOT_TOKEN, skip_pending=True)
app = Flask('')

# Database for learning
DB_FILE = "bot_knowledge.db"

# সব AI প্রদানকারী (বিনামূল্যে এবং এপিআই)
AI_PROVIDERS = {
    "groq": {
        "name": "⚡ Groq",
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "type": "api",
        "enabled": os.getenv("GROQ_API_KEY") is not None,
        "key": os.getenv("GROQ_API_KEY"),
        "model": "llama3-8b-8192"
    },
    "openrouter": {
        "name": "🔀 OpenRouter",
        "url": "https://openrouter.ai/api/v1/chat/completions",
        "type": "api",
        "enabled": os.getenv("OPENROUTER_API_KEY") is not None,
        "key": os.getenv("OPENROUTER_API_KEY"),
        "model": "mistralai/mistral-7b-instruct:free"
    },
    "cohere": {
        "name": "✨ Cohere",
        "url": "https://api.cohere.ai/v1/chat",
        "type": "api",
        "enabled": os.getenv("COHERE_API_KEY") is not None,
        "key": os.getenv("COHERE_API_KEY"),
        "model": "command-r-plus"
    },
    "huggingface": {
        "name": "🤗 HuggingFace",
        "url": "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.1",
        "type": "api",
        "enabled": os.getenv("HUGGINGFACE_TOKEN") is not None,
        "key": os.getenv("HUGGINGFACE_TOKEN"),
        "model": "mistral"
    }
}

# Initialize database
def init_database():
    """Initialize SQLite database"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS knowledge (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question TEXT,
                answer TEXT,
                source TEXT,
                confidence INTEGER DEFAULT 50,
                learned_date TIMESTAMP,
                usage_count INTEGER DEFAULT 0
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ai_responses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ai_provider TEXT,
                question TEXT,
                answer TEXT,
                quality_score INTEGER,
                response_time REAL,
                response_date TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"❌ Database Init Error: {e}")

init_database()

# Local knowledge base
LOCAL_KNOWLEDGE = {
    "হ্যালো": "হ্যালো! আমি একটি সুপার স্মার্ট বট যা সব AI এর সাথে সংযুক্ত। 🤖",
    "হাই": "হাই! আমি সব AI থেকে শিখছি এবং শক্তিশালী হচ্ছি! 💪",
    "আপনি কে": "আমি একটি মাল্টি-AI বট যা সব প্রদানকারী থেকে শিখি! 🚀",
    "সহায়তা": "আমাকে যেকোনো প্রশ্ন করুন, আমি সব AI থেকে সেরা উত্তর দেব! 🤖"
}

@app.route('/')
def home():
    return "🤖 মাল্টি-AI স্মার্ট বট চালু! সব AI এর সাথে সংযুক্ত!"

@app.route('/stats')
def stats():
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM knowledge")
        total_knowledge = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(DISTINCT source) FROM knowledge")
        total_sources = cursor.fetchone()[0]
        conn.close()
        return f"📊 মোট জ্ঞান: {total_knowledge} | AI উৎস: {total_sources}"
    except:
        return "📊 পরিসংখ্যান উপলব্ধ নয়"

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()

# ========== AI Query Functions ==========

def query_groq(question):
    """Query Groq AI"""
    try:
        ai_config = AI_PROVIDERS["groq"]
        if not ai_config["enabled"] or not ai_config.get("key"):
            return None
        
        headers = {
            "Authorization": f"Bearer {ai_config['key']}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": ai_config["model"],
            "messages": [{"role": "user", "content": question}],
            "max_tokens": 300,
            "temperature": 0.7
        }
        
        response = requests.post(ai_config["url"], headers=headers, json=payload, timeout=10)
        print("Groq Status:", response.status_code)
        print("Groq Response:", response.text)

        
        if response.status_code == 200:
            data = response.json()
            answer = data.get('choices', [{}])[0].get('message', {}).get('content', '').strip()
            if answer and len(answer) > 10:
                return answer[:1000]
    except Exception as e:
        print(f"❌ Groq Error: {e}")
    
    return None

def query_openrouter(question):
    """Query OpenRouter"""
    try:
        ai_config = AI_PROVIDERS["openrouter"]
        if not ai_config["enabled"] or not ai_config.get("key"):
            return None
        
        headers = {
            "Authorization": f"Bearer {ai_config['key']}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": ai_config["model"],
            "messages": [{"role": "user", "content": question}],
            "max_tokens": 300
        }
        
        response = requests.post(ai_config["url"], headers=headers, json=payload, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            answer = data.get('choices', [{}])[0].get('message', {}).get('content', '').strip()
            if answer and len(answer) > 10:
                return answer[:1000]
    except Exception as e:
        print(f"❌ OpenRouter Error: {e}")
    
    return None

def query_cohere(question):
    """Query Cohere"""
    try:
        ai_config = AI_PROVIDERS["cohere"]
        if not ai_config["enabled"] or not ai_config.get("key"):
            return None
        
        headers = {
            "Authorization": f"Bearer {ai_config['key']}",
            "Content-Type": "application/json"
        }
        payload = {
            "message": question,
            "max_tokens": 300
        }
        
        response = requests.post(ai_config["url"], headers=headers, json=payload, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            answer = data.get('text', '').strip()
            if answer and len(answer) > 10:
                return answer[:1000]
    except Exception as e:
        print(f"❌ Cohere Error: {e}")
    
    return None

def query_huggingface(question):
    """Query HuggingFace"""
    try:
        ai_config = AI_PROVIDERS["huggingface"]
        if not ai_config["enabled"] or not ai_config.get("key"):
            return None
        
        headers = {"Authorization": f"Bearer {ai_config['key']}"}
        payload = {"inputs": question}
        
        response = requests.post(ai_config["url"], headers=headers, json=payload, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list) and len(data) > 0:
                answer = data[0].get('generated_text', '').strip()
                if answer and len(answer) > 10:
                    # Clean the response
                    answer = answer.replace(question, '').strip()
                    return answer[:1000]
    except Exception as e:
        print(f"❌ HuggingFace Error: {e}")
    
    return None

def get_ai_response(question):
    """Get response from first available AI"""
    ai_funcs = [
        ("Groq", query_groq),
        ("OpenRouter", query_openrouter),
        ("Cohere", query_cohere),
        ("HuggingFace", query_huggingface)
    ]
    
    for ai_name, func in ai_funcs:
        try:
            answer = func(question)
            if answer:
                print(f"✅ {ai_name} Response received")
                return answer, ai_name
        except Exception as e:
            print(f"❌ {ai_name} failed: {e}")
            continue
    
    return None, None

def save_ai_response(ai_name, question, answer):
    """Save AI response to database"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO ai_responses (ai_provider, question, answer, quality_score, response_date)
            VALUES (?, ?, ?, ?, ?)
        ''', (ai_name, question, answer, 85, datetime.now()))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"❌ Save Response Error: {e}")

def save_knowledge(question, answer, source):
    """Save learned knowledge"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO knowledge (question, answer, source, confidence, learned_date)
            VALUES (?, ?, ?, ?, ?)
        ''', (question, answer, source, 85, datetime.now()))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"❌ Save Knowledge Error: {e}")

# ========== Telegram Commands ==========

@bot.message_handler(commands=['start'])
def start(message):
    welcome = """
🤖 *মাল্টি-AI স্মার্ট বটে স্বাগতম!*

আমি যুক্ত আছি:
✅ Groq AI
✅ OpenRouter
✅ Cohere
✅ HuggingFace

📌 *কমান্ড:*
/ais - সংযুক্ত AI দেখুন
/compare - সব AI এর উত্তর
/teach - নতুন কিছু শেখান
/learn - শেখা তথ্য দেখুন
/stats - পরিসংখ্যান
/help - সাহায্য

💡 যেকোনো প্রশ্ন পাঠান!
    """
    try:
        bot.reply_to(message, welcome, parse_mode="Markdown")
    except Exception as e:
        print(f"❌ Start Error: {e}")

@bot.message_handler(commands=['ais'])
def show_ais(message):
    """Show all connected AIs"""
    try:
        text = "🤖 *সংযুক্ত AI প্রদানকারী:*\n\n"
        active_count = 0
        for key, ai in AI_PROVIDERS.items():
            if ai.get("enabled", False):
                text += f"✅ {ai['name']}\n"
                active_count += 1
        
        text += f"\n💪 মোট সক্রিয় AI: *{active_count}*"
        bot.reply_to(message, text, parse_mode="Markdown")
    except Exception as e:
        print(f"❌ Show AIs Error: {e}")

@bot.message_handler(commands=['teach'])
def teach(message):
    """Teach the bot"""
    try:
        text = message.text.replace('/teach', '').strip()
        
        if not text or '|' not in text:
            bot.reply_to(message, "📖 ফরম্যাট: `/teach প্রশ্ন | উত্তর`", parse_mode="Markdown")
            return
        
        parts = text.split('|')
        question = parts[0].strip()
        answer = parts[1].strip()
        
        save_knowledge(question, answer, "Manual Teaching")
        bot.reply_to(message, f"✅ শিখে গেছি!\n\n❓ {question}\n✏️ {answer}")
    except Exception as e:
        print(f"❌ Teach Error: {e}")

@bot.message_handler(commands=['learn'])
def show_knowledge(message):
    """Show learned knowledge"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT question, answer, source FROM knowledge LIMIT 5")
        results = cursor.fetchall()
        conn.close()
        
        if not results:
            bot.reply_to(message, "📚 এখনও কিছু শিখিনি। `/teach` দিয়ে শেখান!")
            return
        
        text = "📚 *আমার শেখা জ্ঞান:*\n\n"
        for q, a, src in results:
            text += f"❓ {q}\n📍 {src}\n✏️ {a[:80]}...\n\n"
        
        bot.reply_to(message, text, parse_mode="Markdown")
    except Exception as e:
        print(f"❌ Learn Error: {e}")

@bot.message_handler(commands=['stats'])
def show_stats(message):
    """Show statistics"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM knowledge")
        total_knowledge = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT source) FROM knowledge")
        total_sources = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM ai_responses")
        total_ai_responses = cursor.fetchone()[0]
        
        conn.close()
        
        stats_text = f"""
📊 *বটের পরিসংখ্যান:*

📚 শেখা বিষয়: *{total_knowledge}*
🤖 AI উৎস: *{total_sources}*
💬 মোট উত্তর: *{total_ai_responses}*

💪 ক্রমাগত শক্তিশালী হচ্ছি!
        """
        bot.reply_to(message, stats_text, parse_mode="Markdown")
    except Exception as e:
        print(f"❌ Stats Error: {e}")

@bot.message_handler(commands=['help'])
def help_cmd(message):
    """Show help"""
    try:
        help_text = """
📖 *কমান্ড সম্পূর্ণ তালিকা:*

🤖 *AI কমান্ড:*
/ais - সব সংযুক্ত AI দেখুন
/compare - সব AI এর উত্তর

📚 *শিক্ষা কমান্ড:*
/teach - নতুন কিছু শেখান
/learn - শেখা বিষয় দেখুন

📊 *তথ্য কমান্ড:*
/stats - পরিসংখ্যান
/help - এই বার্তা

💡 *টিপস:*
- যেকোনো বার্তা পাঠান - উত্তর পাবেন
- `/teach` দিয়ে নিজের জ্ঞান যোগ করুন
        """
        bot.reply_to(message, help_text, parse_mode="Markdown")
    except Exception as e:
        print(f"❌ Help Error: {e}")

@bot.message_handler(commands=['compare'])
def compare_ais(message):
    """Compare all AI responses"""
    try:
        query = message.text.replace('/compare', '').strip()
        
        if not query:
            bot.reply_to(message, "📌 ব্যবহার: `/compare আপনার_প্রশ্ন`", parse_mode="Markdown")
            return
        
        msg = bot.reply_to(message, "🔄 সব AI এর কাছ থেকে উত্তর সংগ্রহ করছি... ⏳")
        
        responses = []
        for ai_name, func in [("Groq", query_groq), ("OpenRouter", query_openrouter), 
                              ("Cohere", query_cohere), ("HuggingFace", query_huggingface)]:
            try:
                answer = func(query)
                if answer:
                    responses.append((ai_name, answer))
            except:
                pass
        
        if responses:
            text = f"🏆 *AI তুলনা ({len(responses)} উত্তর):*\n\n"
            for i, (ai_name, answer) in enumerate(responses, 1):
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}️⃣"
                text += f"{medal} *{ai_name}*\n💬 {answer[:150]}...\n\n"
            
            bot.edit_message_text(text, message.chat.id, msg.message_id, parse_mode="Markdown")
        else:
            bot.edit_message_text(
                "❌ কোনো AI সাড়া দেয়নি।\n\n"
                "সমাধান:\n"
                "1️⃣ API কী যুক্ত করুন `.env` এ\n"
                "2️⃣ ইন্টারনেট চেক করুন\n"
                "3️⃣ `/teach` দিয়ে নিজে শেখান",
                message.chat.id,
                msg.message_id
            )
    except Exception as e:
        print(f"❌ Compare Error: {e}")

@bot.message_handler(func=lambda message: True)
def chat(message):
    """Handle regular messages"""
    try:
        user_text = message.text
        
        # Check local knowledge first
        for key, value in LOCAL_KNOWLEDGE.items():
            if key.lower() in user_text.lower():
                bot.reply_to(message, value)
                return
        
        msg = bot.reply_to(message, "🔄 সেরা উত্তর খুঁজছি... ⏳")
        
        # Get AI response
        answer, source = get_ai_response(user_text)
        
        if answer:
            result_text = f"{answer}\n\n🤖 উৎস: *{source}*"
            save_ai_response(source, user_text, answer)
            save_knowledge(user_text, answer, source)
            bot.edit_message_text(result_text, message.chat.id, msg.message_id, parse_mode="Markdown")
        else:
            bot.edit_message_text(
                "❌ কোনো AI সাড়া দেয়নি।\n\n"
                "সমাধান:\n"
                "1️⃣ API কী যুক্ত করুন `.env` এ\n"
                "2️⃣ ইন্টারনেট চেক করুন\n"
                "3️⃣ `/teach` দিয়ে নিজে শেখান",
                message.chat.id,
                msg.message_id
            )
    except Exception as e:
        print(f"❌ Chat Error: {e}")

if __name__ == "__main__":
    keep_alive()
    print("✅ মাল্টি-AI বট চালু হয়েছে!")
    print("🤖 সব AI এর সাথে সংযুক্ত!")
    
    try:
        bot.infinity_polling(timeout=60, long_polling_timeout=5, skip_pending=True)
    except Exception as e:
        print(f"❌ Polling Error: {e}")
