import telebot
import requests

BOT_TOKEN = "8723812816:AAEi6AbsT8XqTTggYLOqZLlRXAwas3FzdC4"
GEMINI_KEY = "AQ.Ab8RN6K2NYIXnre_Ye-v8zWH8-h3T6gWguC8FYE8mSeF7fjyhg"

bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "✅ Bot Active!")

@bot.message_handler(func=lambda message: True)
def chat(message):
    user_text = message.text
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_KEY}"
    
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
            bot.reply_to(message, f"API Error:\n{result}")
            
    except requests.exceptions.RequestException as e:
        bot.reply_to(message, f"Network/VPN Error: {e}")
    except Exception as e:
        bot.reply_to(message, f"Error: {e}")

print("✅ Bot Running...")
bot.infinity_polling(timeout=60, long_polling_timeout=5)

