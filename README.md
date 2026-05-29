# 🤖 Telegram Gemini Bot

একটি শক্তিশালী Telegram বট যা Gemini AI এর মাধ্যমে স্বয়ংক্রিয় উত্তর প্রদান করে।

## 🚀 ফিচার

- ✅ Gemini AI দ্বারা চালিত চ্যাট
- ✅ Dynamic API Key জেনারেশন
- ✅ নিরাপদ credential management
- ✅ Error handling এবং fallback সিস্টেম
- ✅ Flask সার্ভার রেডিনেস চেক

## 📋 প্রয়োজনীয় জিনিস

- Python 3.8+
- Telegram Bot Token ([@BotFather](https://t.me/botfather) থেকে)
- Gemini API Key (Google AI Studio থেকে)

## 🔧 ইনস্টলেশন

### ১. Repository Clone করুন:
```bash
git clone https://github.com/Kawserkp66/requirements.txt.git
cd requirements.txt
```

### ২. Virtual Environment তৈরি করুন:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# অথবা
venv\\Scripts\\activate  # Windows
```

### ३. Dependencies ইনস্টল করুন:
```bash
pip install -r requirements.txt
```

### ४. `.env` ফাইল তৈরি করুন:
```bash
cp .env.example .env
```

### ५. আপনার API কী যোগ করুন (`.env` ফাইলে):
```
BOT_TOKEN=আপনার_টেলিগ্রাম_বট_টোকেন
GEMINI_KEY=আপনার_জেমিনি_এপিআই_কী
```

## ▶️ রান করুন

```bash
python bot.py
```

## 📝 কমান্ড

- `/start` - বট শুরু করুন
- `/newkey` - নতুন API Key তৈরি করুন
- `/keys` - সব সক্রিয় Key দেখুন
- সাধারণ বার্তা পাঠান - Gemini AI উত্তর পাবেন

## ⚠️ নিরাপত্তা টিপস

- ✅ কখনও API কী কোডে হার্ডকোড করবেন না
- ✅ সবসময় `.env` ব্যবহার করুন
- ✅ `.gitignore` তে `.env` যোগ করুন
- ✅ পাবলিক রিপোতে কী কখনও কমিট করবেন না
- ✅ নিয়মিত আপনার API কী রিজেনারেট করুন

## 🔄 কীভাবে কাজ করে

1. ব্যবহারকারী বটে মেসেজ পাঠায়
2. বট Gemini API তে রিকোয়েস্ট করে
3. Gemini AI উত্তর দেয়
4. বট উত্তর ব্যবহারকারীকে পাঠায়
5. যদি Key এক্সপায়ার হয়, নতুন Key তৈরি হয়

## 📄 লাইসেন্স

MIT License

## 👨‍💻 লেখক

Kawserkp66

## 🙏 সহায়তা

যদি কোন সমস্যা হয়, GitHub Issues তে রিপোর্ট করুন।
