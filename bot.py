import os
import json
import requests
from threading import Thread
from flask import Flask
import telebot
from dotenv import load_dotenv
from datetime import datetime
from bs4 import BeautifulSoup
import sqlite3
from collections import defaultdict

# Load environment variables
load_dotenv()

# Get Bot Token only (Gemini API not needed!)
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN not found in environment variables!")

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask('')

# Database for learning
DB_FILE = "bot_knowledge.db"

# Initialize database
def init_database():
    """Initialize SQLite database for storing knowledge"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS knowledge (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT UNIQUE,
            answer TEXT,
            confidence INTEGER DEFAULT 50,
            learned_date TIMESTAMP,
            usage_count INTEGER DEFAULT 0
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_interactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            question TEXT,
            answer TEXT,
            feedback TEXT,
            interaction_date TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

init_database()

# Knowledge base responses (Local AI)
LOCAL_KNOWLEDGE = {
    "হ্যালো": "হ্যালো! আমি আপনার সাহায্য করতে এখানে আছি। 😊",
    "হাই": "হাই! কেমন আছেন? কিভাবে আপনাকে সাহায্য করতে পারি?",
    "স্বাগতম": "আপনাকে স্বাগতম! আমাকে যেকোনো প্রশ্ন জিজ্ঞাসা করুন। 🎯",
    "আপনি কে": "আমি একটি স্মার্ট টেলিগ্রাম বট যা নিজে শিখে এবং বৃদ্ধি পায়। 🤖",
    "কিভাবে আছেন": "আমি ভাল আছি, ধন্যবাদ! আপনি কেমন আছেন?",
    "সাহায্য": "আমি এই কাজগুলি করতে পারি:\n/learn - নতুন কিছু শিখুন\n/teach - আমাকে কিছু শেখান\n/web - ওয়েবসাইট থেকে জ্ঞান সংগ্রহ করুন\n/stats - আমার অগ্রগতি দেখুন",
    "ধন্যবাদ": "আপনার স্বাগতম! আমাকে আরো কিছু জিজ্ঞাসা করুন। 💪",
}

@app.route('/')
def home():
    return "🤖 স্মার্ট বট চালু আছে! নিজে শিখছে এবং বৃদ্ধি পাচ্ছে।"

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()

def get_knowledge_from_db(question):
    """Fetch answer from database"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("SELECT answer, confidence FROM knowledge WHERE question LIKE ?", (f"%{question}%",))
    result = cursor.fetchone()
    conn.close()
    
    return result

def save_knowledge(question, answer, confidence=70):
    """Save learned knowledge to database"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT OR REPLACE INTO knowledge (question, answer, confidence, learned_date)
            VALUES (?, ?, ?, ?)
        ''', (question, answer, confidence, datetime.now()))
        conn.commit()
    except:
        pass
    finally:
        conn.close()

def search_web(query):
    """Search web for information (using DuckDuckGo or similar)"""
    try:
        # Try to fetch from a simple API or search
        headers = {'User-Agent': 'Mozilla/5.0'}
        
        # Using DuckDuckGo for search (no API key needed)
        search_url = f"https://html.duckduckgo.com/?q={query}"
        response = requests.get(search_url, headers=headers, timeout=5)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            # Extract snippets
            results = soup.find_all('span', class_='snippet', limit=3)
            
            if results:
                answer = "📚 ওয়েব থেকে পাওয়া তথ্য:\n\n"
                for i, result in enumerate(results, 1):
                    text = result.get_text(strip=True)
                    if text:
                        answer += f"{i}. {text[:200]}...\n\n"
                return answer
    except:
        pass
    
    return None

def get_response(user_text):
    """Get response using local knowledge"""
    user_text_lower = user_text.lower().strip()
    
    # Check database first
    db_result = get_knowledge_from_db(user_text_lower)
    if db_result:
        return db_result[0], db_result[1]
    
    # Check local knowledge
    for key, value in LOCAL_KNOWLEDGE.items():
        if key.lower() in user_text_lower:
            return value, 90
    
    # Try web search
    web_answer = search_web(user_text)
    if web_answer:
        return web_answer, 75
    
    return None, 0

def update_usage(question):
    """Update usage count"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("UPDATE knowledge SET usage_count = usage_count + 1 WHERE question LIKE ?", (f"%{question}%",))
    conn.commit()
    conn.close()

@bot.message_handler(commands=['start'])
def start(message):
    welcome_text = """
🤖 স্বাগতম স্মার্ট বটে!

আমি একটি স্ব-শিক্ষণ বট যা:
✅ নিজে শিখে
✅ ওয়েবসাইট থেকে জ্ঞান সংগ্রহ করে
✅ প্রতিটি প্রশ্নে আরো স্মার্ট হয়

কমান্ড:
/help - সাহায্য
/teach - আমাকে কিছু শেখান
/learn - জ্ঞান দেখুন
/web - ওয়েব সার্চ করুন
/stats - আমার অগ্রগতি
/about - আমার সম্পর্কে
    """
    bot.reply_to(message, welcome_text)

@bot.message_handler(commands=['teach'])
def teach(message):
    """Teach the bot new information"""
    text = message.text.replace('/teach', '').strip()
    
    if not text:
        bot.reply_to(message, "📖 ফরম্যাট: `/teach প্রশ্ন | উত্তর`\n\nউদাহরণ:\n`/teach ঢাকা কোথায় | ঢাকা বাংলাদেশের রাজধানী`", parse_mode="Markdown")
        return
    
    if '|' not in text:
        bot.reply_to(message, "❌ '|' দিয়ে প্রশ্ন এবং উত্তর আলাদা করুন!")
        return
    
    parts = text.split('|')
    question = parts[0].strip()
    answer = parts[1].strip()
    
    save_knowledge(question, answer, 85)
    bot.reply_to(message, f"✅ শিখে গেছি!\n\n❓ {question}\n\n✏️ {answer}")

@bot.message_handler(commands=['web'])
def web_search(message):
    """Search web for information"""
    query = message.text.replace('/web', '').strip()
    
    if not query:
        bot.reply_to(message, "🔍 কি সার্চ করতে চান?\n\nউদাহরণ: `/web বাংলাদেশের রাজধানী`", parse_mode="Markdown")
        return
    
    bot.reply_to(message, f"🔍 খুঁজছি: *{query}*...", parse_mode="Markdown")
    
    result = search_web(query)
    
    if result:
        save_knowledge(query, result, 70)
        bot.send_message(message.chat.id, result)
    else:
        bot.reply_to(message, "❌ কিছু তথ্য পাই নাই। আপনি শেখাতে পারেন: `/teach` ব্যবহার করুন", parse_mode="Markdown")

@bot.message_handler(commands=['learn'])
def show_knowledge(message):
    """Show all learned knowledge"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("SELECT question, answer, confidence FROM knowledge LIMIT 5")
    results = cursor.fetchall()
    conn.close()
    
    if not results:
        bot.reply_to(message, "📚 এখনও কোনো জ্ঞান শিখি নাই। `/teach` দিয়ে শেখান!")
        return
    
    text = "📚 আমার জ্ঞান:\n\n"
    for q, a, conf in results:
        text += f"❓ {q}\n✏️ {a[:100]}...\n📊 আত্মবিশ্বাস: {conf}%\n\n"
    
    bot.reply_to(message, text)

@bot.message_handler(commands=['stats'])
def show_stats(message):
    """Show bot statistics"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM knowledge")
    total_knowledge = cursor.fetchone()[0]
    
    cursor.execute("SELECT AVG(confidence) FROM knowledge")
    avg_confidence = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT SUM(usage_count) FROM knowledge")
    total_usage = cursor.fetchone()[0] or 0
    
    conn.close()
    
    stats_text = f"""
📊 বটের অগ্রগতি:

📚 শেখা বিষয়: {total_knowledge}
📈 গড় আত্মবিশ্বাস: {avg_confidence:.1f}%
🎯 মোট ব্যবহার: {total_usage}

💪 আমি আরো শক্তিশালী হচ্ছি!
    """
    
    bot.reply_to(message, stats_text)

@bot.message_handler(commands=['about'])
def about(message):
    """About the bot"""
    about_text = """
🤖 আমি একটি স্মার্ট বট

বৈশিষ্ট্য:
✅ স্থানীয় জ্ঞান ব্যবস্থাপনা
✅ ওয়েব সার্চ ক্ষমতা
✅ স্বয়ংক্রিয় শিক্ষা
✅ প্রতিটি মিথস্ক্রিয়া থেকে শিখছি
✅ কোনো এপিআই প্রয়োজন নেই!

আমাকে শেখান এবং আমি আরো শক্তিশালী হব! 💪
    """
    bot.reply_to(message, about_text)

@bot.message_handler(commands=['help'])
def help_command(message):
    """Show help"""
    help_text = """
📖 আমাকে এভাবে ব্যবহার করুন:

🎯 কমান্ড:
/start - শুরু করুন
/teach - আমাকে শেখান (প্রশ্ন | উত্তর)
/learn - আমার জ্ঞান দেখুন
/web - ওয়েবসাইটে সার্চ করুন
/stats - আমার উন্নতি দেখুন
/about - আমার সম্পর্কে
/help - এই বার্তা

💡 উদাহরণ:
`/teach ঢাকা কোথায় | বাংলাদেশের রাজধানী`
`/web পৃথিবীর সবচেয়ে বড় দেশ`

যেকোনো বার্তা পাঠান - আমি উত্তর দেওয়ার চেষ্টা করব! 🎯
    """
    bot.reply_to(message, help_text)

@bot.message_handler(func=lambda message: True)
def chat(message):
    """Handle regular messages"""
    user_text = message.text
    
    # Get response
    response, confidence = get_response(user_text)
    
    if response:
        update_usage(user_text)
        
        if confidence > 80:
            bot.reply_to(message, f"{response}\n\n✅ আত্মবিশ্বাস: {confidence}%")
        else:
            bot.reply_to(message, f"{response}\n\n⚠️ আত্মবিশ্বাস: {confidence}%\n\n(যদি ভুল হয়, আমাকে শেখান: `/teach` ব্যবহার করুন)")
    else:
        bot.reply_to(message, """
❓ আমি এই প্রশ্নের উত্তর জানি না।

আপনি আমাকে শেখাতে পারেন:
`/teach আপনার_প্রশ্ন | আপনার_উত্তর`

অথবা আমি ওয়েবে সার্চ করতে পারি:
`/web আপনার_প্রশ্ন`
        """)

if __name__ == "__main__":
    keep_alive()
    print("✅ স্মার্ট বট চালু হয়েছে!")
    print("📚 নিজে শিখছে এবং বৃদ্ধি পাচ্ছে...")
    print("💪 Gemini API প্রয়োজন নেই!")
    bot.infinity_polling(timeout=60, long_polling_timeout=5)
