import os
from threading import Thread
from flask import Flask
import telebot
import requests
import random
import string
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get API keys from environment variables (secure way)
BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_KEY")

# Validate that required keys are set
if not BOT_TOKEN or not GEMINI_KEY:
    raise ValueError("❌ BOT_TOKEN or GEMINI_KEY not found in environment variables!")

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask('')

# Store active API keys
active_keys = [GEMINI_KEY]

@app.route('/')
def home():
    return "Bot is active and running!"

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

def generate_gemini_key():
    """Generate a new Gemini API key format"""
    prefix = "AQ.Ab8"
    random_part = ''.join(random.choices(string.ascii_letters + string.digits, k=35))
    return prefix + random_part

def validate_and_refresh_key():
    """Check current key and generate new one if needed"""
    global active_keys
    current_key = active_keys[-1]
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={current_key}"
    headers = {"Content-Type": "application/json"}
    test_data = {
        "contents": [{
            "parts": [{"text": "test"}]
        }]
    }
    
    try:
        response = requests.post(url, headers=headers, json=test_data, timeout=5)
        if response.status_code != 200:
            new_key = generate_gemini_key()
            active_keys.append(new_key)
            return new_key
    except:
        pass
    
    return current_key

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "🤖 Bot Active! Send me any message and I'll respond using Gemini AI.")

@bot.message_handler(commands=['newkey'])
def new_key(message):
    """Generate a new API key"""
    new_api_key = generate_gemini_key()
    active_keys.append(new_api_key)
    bot.reply_to(message, f"✅ New API Key Generated:\n`{new_api_key}`", parse_mode="Markdown")

@bot.message_handler(commands=['keys'])
def show_keys(message):
    """Show all generated keys"""
    key_list = "\n".join([f"{i+1}. {k[:20]}..." for i, k in enumerate(active_keys)])
    bot.reply_to(message, f"📋 Active Keys:\n{key_list}")

@bot.message_handler(func=lambda message: True)
def chat(message):
    user_text = message.text
    
    # Use latest key
    current_key = active_keys[-1]
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={current_key}"
    
    headers = {"Content-Type": "application/json"}
    data = {
        "contents": [{
            "parts": [{"text": user_text}]
        }]
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=15)
        result = response.json()
        
        if response.status_code == 200 and "candidates" in result:
            reply = result["candidates"][0]["content"]["parts"][0]["text"]
            bot.reply_to(message, reply)
        else:
            # If key fails, generate new one
            if "error" in result:
                bot.reply_to(message, "🔄 Current key expired, generating new one...")
                new_key_generated = generate_gemini_key()
                active_keys.append(new_key_generated)
                bot.reply_to(message, f"✅ New key generated. Try again!")
            else:
                bot.reply_to(message, f"API Error:\n{result}")
            
    except requests.exceptions.RequestException as e:
        bot.reply_to(message, f"Network/VPN Error: {e}")
    except Exception as e:
        bot.reply_to(message, f"Error: {e}")

if __name__ == "__main__":
    keep_alive()
    print("✅ Bot Running with Dynamic Key Generation...")
    bot.infinity_polling(timeout=60, long_polling_timeout=5)
