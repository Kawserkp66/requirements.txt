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
import concurrent.futures

# Load environment variables
load_dotenv()

# Get Bot Token only
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN not found in environment variables!")

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask('')

# Database for learning
DB_FILE = "bot_knowledge.db"

# সব AI প্রদানকারী (বিনামূল্যে এবং এপিআই)
AI_PROVIDERS = {
    "local": {
        "name": "📱 স্থানীয় জ্ঞান",
        "type": "local",
        "enabled": True
    },
    "ollama": {
        "name": "🦙 Ollama (স্থানীয় মডেল)",
        "url": "http://localhost:11434/api/generate",
        "type": "local_llm",
        "enabled": True,
        "models": ["mistral", "llama2", "neural-chat"]
    },
    "together": {
        "name": "🚀 Together AI",
        "url": "https://api.together.xyz/inference",
        "type": "api",
        "enabled": os.getenv("TOGETHER_API_KEY") is not None,
        "key": os.getenv("TOGETHER_API_KEY"),
        "models": ["mistralai/Mistral-7B", "meta-llama/Llama-2-13b"]
    },
    "openrouter": {
        "name": "🔀 OpenRouter",
        "url": "https://openrouter.ai/api/v1/chat/completions",
        "type": "api",
        "enabled": os.getenv("OPENROUTER_API_KEY") is not None,
        "key": os.getenv("OPENROUTER_API_KEY"),
        "models": ["mistralai/mistral-7b-instruct", "meta-llama/llama-2-13b"]
    },
    "huggingface": {
        "name": "🤗 HuggingFace",
        "url": "https://api-inference.huggingface.co/models",
        "type": "api",
        "enabled": os.getenv("HUGGINGFACE_TOKEN") is not None,
        "key": os.getenv("HUGGINGFACE_TOKEN"),
        "models": ["gpt2", "distilbert-base-uncased"]
    },
    "cohere": {
        "name": "✨ Cohere",
        "url": "https://api.cohere.ai/v1/generate",
        "type": "api",
        "enabled": os.getenv("COHERE_API_KEY") is not None,
        "key": os.getenv("COHERE_API_KEY")
    },
    "groq": {
        "name": "⚡ Groq",
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "type": "api",
        "enabled": os.getenv("GROQ_API_KEY") is not None,
        "key": os.getenv("GROQ_API_KEY"),
        "models": ["mixtral-8x7b-32768", "llama2-70b"]
    },
    "replicate": {
        "name": "🎬 Replicate",
        "url": "https://api.replicate.com/v1/predictions",
        "type": "api",
        "enabled": os.getenv("REPLICATE_API_KEY") is not None,
        "key": os.getenv("REPLICATE_API_KEY")
    }
}

# Initialize database
def init_database():
    """Initialize SQLite database"""
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
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ai_comparison (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT,
            ai_responses TEXT,
            best_ai TEXT,
            user_feedback TEXT,
            created_date TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

init_database()

# Local knowledge base
LOCAL_KNOWLEDGE = {
    "হ্যালো": "হ্যালো! আমি একটি সুপার স্মার্ট বট যা সব AI এর সাথে সংযুক্ত। 🤖",
    "হাই": "হাই! আমি সব AI থেকে শিখছি এবং শক্তিশালী হচ্ছি! 💪",
    "আপনি কে": "আমি একটি মাল্টি-AI বট যা সব প্রদানকারী থেকে শিখি! 🚀",
}

@app.route('/')
def home():
    return "🤖 মাল্টি-AI স্মার্ট বট চালু! সব AI এর সাথে সংযুক্ত!"

@app.route('/stats')
def stats():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM knowledge")
    total_knowledge = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(DISTINCT source) FROM knowledge")
    total_sources = cursor.fetchone()[0]
    conn.close()
    return f"📊 মোট জ্ঞান: {total_knowledge} | AI উৎস: {total_sources}"

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port, debug=False)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()

# ========== AI Query Functions ==========

def query_ollama(question):
    """Query local Ollama"""
    try:
        ai_config = AI_PROVIDERS["ollama"]
        payload = {
            "model": "mistral",
            "prompt": question,
            "stream": False
        }
        response = requests.post(ai_config["url"], json=payload, timeout=10)
        if response.status_code == 200:
            data = response.json()
            answer = data.get('response', '')
            if answer:
                return answer[:500], "Ollama", 85, response.elapsed.total_seconds()
    except Exception as e:
        print(f"❌ Ollama Error: {e}")
    return None, None, 0, 0

def query_together_ai(question):
    """Query Together AI"""
    try:
        ai_config = AI_PROVIDERS["together"]
        if not ai_config["enabled"]:
            return None, None, 0, 0
        
        headers = {"Authorization": f"Bearer {ai_config['key']}"}
        payload = {
            "model": "mistralai/Mistral-7B-Instruct-v0.1",
            "prompt": question,
            "max_tokens": 300
        }
        response = requests.post(ai_config["url"], headers=headers, json=payload, timeout=10)
        if response.status_code == 200:
            data = response.json()
            answer = data.get('output', {}).get('choices', [{}])[0].get('text', '')
            if answer:
                return answer[:500], "Together AI", 80, response.elapsed.total_seconds()
    except Exception as e:
        print(f"❌ Together AI Error: {e}")
    return None, None, 0, 0

def query_openrouter(question):
    """Query OpenRouter"""
    try:
        ai_config = AI_PROVIDERS["openrouter"]
        if not ai_config["enabled"]:
            return None, None, 0, 0
        
        headers = {
            "Authorization": f"Bearer {ai_config['key']}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "mistralai/mistral-7b-instruct:free",
            "messages": [{"role": "user", "content": question}],
            "max_tokens": 300
        }
        response = requests.post(ai_config["url"], headers=headers, json=payload, timeout=10)
        if response.status_code == 200:
            data = response.json()
            answer = data.get('choices', [{}])[0].get('message', {}).get('content', '')
            if answer:
                return answer[:500], "OpenRouter", 85, response.elapsed.total_seconds()
    except Exception as e:
        print(f"❌ OpenRouter Error: {e}")
    return None, None, 0, 0

def query_huggingface(question):
    """Query HuggingFace"""
    try:
        ai_config = AI_PROVIDERS["huggingface"]
        if not ai_config["enabled"]:
            return None, None, 0, 0
        
        headers = {"Authorization": f"Bearer {ai_config['key']}"}
        url = f"{ai_config['url']}/gpt2"
        payload = {"inputs": question}
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list) and len(data) > 0:
                answer = data[0].get('generated_text', '')
                if answer:
                    return answer[:500], "HuggingFace", 75, response.elapsed.total_seconds()
    except Exception as e:
        print(f"❌ HuggingFace Error: {e}")
    return None, None, 0, 0

def query_cohere(question):
    """Query Cohere"""
    try:
        ai_config = AI_PROVIDERS["cohere"]
        if not ai_config["enabled"]:
            return None, None, 0, 0
        
        headers = {"Authorization": f"Bearer {ai_config['key']}"}
        payload = {
            "prompt": question,
            "max_tokens": 300,
            "temperature": 0.8
        }
        response = requests.post(ai_config["url"], headers=headers, json=payload, timeout=10)
        if response.status_code == 200:
            data = response.json()
            answer = data.get('generations', [{}])[0].get('text', '')
            if answer:
                return answer[:500], "Cohere", 80, response.elapsed.total_seconds()
    except Exception as e:
        print(f"❌ Cohere Error: {e}")
    return None, None, 0, 0

def query_groq(question):
    """Query Groq"""
    try:
        ai_config = AI_PROVIDERS["groq"]
        if not ai_config["enabled"]:
            return None, None, 0, 0
        
        headers = {
            "Authorization": f"Bearer {ai_config['key']}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "mixtral-8x7b-32768",
            "messages": [{"role": "user", "content": question}],
            "max_tokens": 300
        }
        response = requests.post(ai_config["url"], headers=headers, json=payload, timeout=10)
        if response.status_code == 200:
            data = response.json()
            answer = data.get('choices', [{}])[0].get('message', {}).get('content', '')
            if answer:
                return answer[:500], "Groq", 90, response.elapsed.total_seconds()
    except Exception as e:
        print(f"❌ Groq Error: {e}")
    return None, None, 0, 0

def query_all_ais(question):
    """Query all available AIs in parallel"""
    responses = []
    
    ai_functions = [
        ("Local", lambda: (None, None, 0, 0)),  # Skip local for now
        ("Ollama", query_ollama),
        ("Together", query_together_ai),
        ("OpenRouter", query_openrouter),
        ("HuggingFace", query_huggingface),
        ("Cohere", query_cohere),
        ("Groq", query_groq),
    ]
    
    # Use ThreadPoolExecutor for parallel queries
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = {}
        for name, func in ai_functions[1:]:  # Skip local
            future = executor.submit(func, question)
            futures[future] = name
        
        # ✅ সমাধান: সঠিক error handling
        for future in concurrent.futures.as_completed(futures):
            try:
                answer, source, score, time_taken = future.result(timeout=5)
                if answer:
                    responses.append({
                        'answer': answer,
                        'source': source,
                        'score': score,
                        'time': time_taken
                    })
            except concurrent.futures.TimeoutError:
                print(f"⏱️ Timeout: {futures[future]}")
            except Exception as e:
                print(f"❌ Error in {futures[future]}: {e}")
    
    return responses

def save_ai_response(ai_name, question, answer, score):
    """Save AI response to database"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO ai_responses (ai_provider, question, answer, quality_score, response_date)
            VALUES (?, ?, ?, ?, ?)
        ''', (ai_name, question, answer, score, datetime.now()))
        conn.commit()
    except Exception as e:
        print(f"❌ Database Error: {e}")
    finally:
        conn.close()

def save_knowledge(question, answer, source, confidence=70):
    """Save learned knowledge"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO knowledge (question, answer, source, confidence, learned_date)
            VALUES (?, ?, ?, ?, ?)
        ''', (question, answer, source, confidence, datetime.now()))
        conn.commit()
    except Exception as e:
        print(f"❌ Database Error: {e}")
    finally:
        conn.close()

def get_response(user_text):
    """Get best response from all AIs"""
    user_text_lower = user_text.lower().strip()
    
    # Check local knowledge first
    for key, value in LOCAL_KNOWLEDGE.items():
        if key.lower() in user_text_lower:
            return value, "Local", 95
    
    # Query all AIs
    responses = query_all_ais(user_text)
    
    if responses:
        # Sort by quality score and select best
        best = max(responses, key=lambda x: x['score'])
        
        # Save all responses
        for resp in responses:
            save_ai_response(resp['source'], user_text, resp['answer'], resp['score'])
        
        # Save best one as knowledge
        save_knowledge(user_text, best['answer'], best['source'], best['score'])
        
        return best['answer'], best['source'], best['score']
    
    return None, None, 0

# ========== Telegram Commands ==========

@bot.message_handler(commands=['start'])
def start(message):
    welcome = """
🤖 মাল্টি-AI স্মার্ট বটে স্বাগতম!

আমি যুক্ত আছি:
✅ Ollama (স্থানীয়)
✅ Together AI
✅ OpenRouter
✅ HuggingFace
✅ Cohere
✅ Groq
✅ আরো অনেক AI!

কমান্ড:
/ais - সব সংযুক্ত AI দেখুন
/compare - সব AI এর উত্তর তুলনা করুন
/teach - নতুন কিছু শেখান
/learn - শেখা তথ্য দেখুন
/stats - আমার অগ্রগতি
/help - সাহায্য
    """
    bot.reply_to(message, welcome)

@bot.message_handler(commands=['ais'])
def show_ais(message):
    """Show all connected AIs"""
    text = "🤖 সংযুক্ত AI প্রদানকারী:\n\n"
    
    active_count = 0
    for key, ai in AI_PROVIDERS.items():
        if ai.get("enabled", False):
            text += f"✅ {ai['name']}\n"
            active_count += 1
    
    text += f"\n💪 মোট সক্রিয় AI: {active_count}"
    bot.reply_to(message, text)

@bot.message_handler(commands=['compare'])
def compare_ais(message):
    """Compare all AI responses"""
    query = message.text.replace('/compare', '').strip()
    
    if not query:
        bot.reply_to(message, "📌 কমান্ড: `/compare আপনার_প্রশ্ন`", parse_mode="Markdown")
        return
    
    msg = bot.reply_to(message, f"🔄 স�� AI এর কাছ থেকে উত্তর সংগ্রহ করছি... ⏳")
    
    responses = query_all_ais(query)
    
    if responses:
        # Sort by score
        responses.sort(key=lambda x: x['score'], reverse=True)
        
        text = f"🏆 AI তুলনা ({len(responses)} উত্তর):\n\n"
        
        for i, resp in enumerate(responses, 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}️⃣"
            text += f"{medal} **{resp['source']}** (স্কোর: {resp['score']}%, সময়: {resp['time']:.2f}s)\n"
            text += f"💬 {resp['answer'][:150]}...\n\n"
        
        bot.edit_message_text(text, message.chat.id, msg.message_id)
    else:
        # ✅ সমাধান: Line 466 টাইপো ঠিক করা হয়েছে
        bot.edit_message_text(
            "❌ কোনো AI সাড়া দেয়নি।\n\n"
            "সমাধান:\n"
            "1️⃣ Ollama চালু করুন: `ollama run mistral`\n"
            "2️⃣ API কী যোগ করুন: `.env` এ\n"
            "3️⃣ `/teach` দিয়ে নিজে শেখান",
            message.chat.id,
            msg.message_id
        )

@bot.message_handler(commands=['teach'])
def teach(message):
    """Teach the bot"""
    text = message.text.replace('/teach', '').strip()
    
    if not text or '|' not in text:
        bot.reply_to(message, "📖 ফরম্যাট: `/teach প্রশ্ন | উত্তর`", parse_mode="Markdown")
        return
    
    parts = text.split('|')
    question = parts[0].strip()
    answer = parts[1].strip()
    
    save_knowledge(question, answer, "Manual Teaching", 90)
    bot.reply_to(message, f"✅ শিখে গেছি!\n\n❓ {question}\n✏️ {answer}")

@bot.message_handler(commands=['learn'])
def show_knowledge(message):
    """Show learned knowledge"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT question, answer, source FROM knowledge LIMIT 5")
    results = cursor.fetchall()
    conn.close()
    
    if not results:
        bot.reply_to(message, "📚 এখনও কিছু শিখিনি। `/teach` দিয়ে শেখান!")
        return
    
    text = "📚 আমার শেখা জ্ঞান:\n\n"
    for q, a, src in results:
        text += f"❓ {q}\n📍 উৎস: {src}\n✏️ {a[:80]}...\n\n"
    
    bot.reply_to(message, text)

@bot.message_handler(commands=['stats'])
def show_stats(message):
    """Show statistics"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM knowledge")
    total_knowledge = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(DISTINCT source) FROM knowledge")
    total_sources = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM ai_responses")
    total_ai_responses = cursor.fetchone()[0]
    
    cursor.execute("SELECT AVG(quality_score) FROM ai_responses")
    avg_score = cursor.fetchone()[0] or 0
    
    conn.close()
    
    stats_text = f"""
📊 বটের পরিসংখ্যান:

📚 মোট শেখা বিষয়: {total_knowledge}
🤖 সক্রিয় AI উৎস: {total_sources}
💬 মোট AI প্রতিক্রিয়া: {total_ai_responses}
⭐ গড় AI স্কোর: {avg_score:.1f}%

💪 ক্রমাগত শক্তিশালী হচ্ছি!
    """
    bot.reply_to(message, stats_text)

@bot.message_handler(commands=['help'])
def help_cmd(message):
    """Show help"""
    help_text = """
📖 কমান্ড সম্পূর্ণ তালিকা:

🤖 AI কমান্ড:
/ais - সব সংযুক্ত AI দেখুন
/compare - AI তুলনা করুন

📚 শিক্ষা কমান্ড:
/teach - নতুন কিছু শেখান
/learn - শেখা বিষয় দেখুন

📊 তথ্য কমান্ড:
/stats - পরিসংখ্যান
/help - এই বার্তা

💡 টিপস:
- যেকোনো বার্তা পাঠান - সব AI উত্তর দেবে
- `/compare` দিয়ে সব AI তুলনা করুন
- `/teach` দিয়ে নিজের জ্ঞান যোগ করুন
    """
    bot.reply_to(message, help_text)

@bot.message_handler(func=lambda message: True)
def chat(message):
    """Handle regular messages"""
    user_text = message.text
    
    msg = bot.reply_to(message, "🔄 সব AI এর কাছ থেকে সেরা উত্তর খুঁজছি... ⏳")
    
    response, source, score = get_response(user_text)
    
    if response:
        result_text = f"{response}\n\n"
        result_text += f"🤖 উৎস: **{source}**\n"
        result_text += f"⭐ আত্মবিশ্বাস: {score}%"
        
        if score < 70:
            result_text += "\n\n💡 আমাকে শেখান: `/teach` ব্যবহার করুন"
        
        bot.edit_message_text(result_text, message.chat.id, msg.message_id)
    else:
        bot.edit_message_text(
            "❌ কোনো AI সাড়া দেয়নি।\n\n"
            "সমাধান:\n"
            "1️⃣ Ollama চালু করুন: `ollama run mistral`\n"
            "2️⃣ API কী যোগ করুন: `.env` এ\n"
            "3️⃣ `/teach` দিয়ে নিজে শেখান",
            message.chat.id,
            msg.message_id
        )

if __name__ == "__main__":
    keep_alive()
    print("✅ মাল্টি-AI বট চালু হয়েছে!")
    print("🤖 সব AI এর সাথে সংযুক্ত!")
    print("💪 প্যারালাল কোয়েরিং সক্রিয়!")
    bot.infinity_polling(timeout=60, long_polling_timeout=5)
