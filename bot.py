import telebot
import pymongo
import os
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

TOKEN = os.getenv("BOT_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")
WEB_APP_URL = os.getenv("WEB_APP_URL")

bot = telebot.TeleBot(TOKEN)
client = pymongo.MongoClient(MONGO_URI)
db = client["telegram_bot"]
users = db["users"]

# 📌 /start Command - User Registration & Referral System
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.chat.id
    referred_by = None

    if " " in message.text:
        referred_by = message.text.split()[1]

    user = users.find_one({"user_id": user_id})

    if not user:
        users.insert_one({"user_id": user_id, "balance": 0, "referred_by": referred_by})
        if referred_by:
            users.update_one({"user_id": int(referred_by)}, {"$inc": {"balance": 10}})  # Referral reward

    balance = users.find_one({"user_id": user_id})["balance"]
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🎡 Spin & Earn", web_app=WebAppInfo(url=WEB_APP_URL)))
    markup.add(InlineKeyboardButton("💰 Check Balance", callback_data="balance"))
    markup.add(InlineKeyboardButton("🎁 Claim Daily Bonus", callback_data="daily_bonus"))
    markup.add(InlineKeyboardButton("📢 Join Channel & Earn", callback_data="join_channel"))
    markup.add(InlineKeyboardButton("💳 Withdraw Money", callback_data="withdraw"))

    bot.send_message(user_id, f"👋 Welcome! Your balance: ₹{balance}\nRefer & Earn ₹10 per friend!\nYour link: `https://t.me/yourbot?start={user_id}`", parse_mode="Markdown", reply_markup=markup)

# 📌 Check Balance
@bot.callback_query_handler(func=lambda call: call.data == "balance")
def check_balance(call):
    balance = users.find_one({"user_id": call.message.chat.id})["balance"]
    bot.answer_callback_query(call.id, f"💰 Your Balance: ₹{balance}")

# 📌 Daily Bonus (₹5 Per Day)
@bot.callback_query_handler(func=lambda call: call.data == "daily_bonus")
def daily_bonus(call):
    user = users.find_one({"user_id": call.message.chat.id})
    users.update_one({"user_id": call.message.chat.id}, {"$inc": {"balance": 5}})
    bot.answer_callback_query(call.id, "🎁 You claimed ₹5 daily bonus!")

# 📌 Join Telegram Channel Task
@bot.callback_query_handler(func=lambda call: call.data == "join_channel")
def join_channel(call):
    user_id = call.message.chat.id
    bot.answer_callback_query(call.id, "✅ Complete the task and reply 'Done' to get ₹10.")
    bot.register_next_step_handler(call.message, verify_channel_join)

def verify_channel_join(message):
    if message.text.lower() == "done":
        users.update_one({"user_id": message.chat.id}, {"$inc": {"balance": 10}})
        bot.send_message(message.chat.id, "✅ ₹10 credited for joining the channel!")

# 📌 Withdrawal System
@bot.callback_query_handler(func=lambda call: call.data == "withdraw")
def withdraw(call):
    bot.send_message(call.message.chat.id, "💳 Send your UPI ID for withdrawal:")
    bot.register_next_step_handler(call.message, process_withdrawal)

def process_withdrawal(message):
    upi_id = message.text
    user = users.find_one({"user_id": message.chat.id})

    if "@" not in upi_id:
        bot.send_message(message.chat.id, "❌ Invalid UPI ID. Please try again.")
        return
    
    admin_id = 123456789  # अपना Telegram Admin ID डालें
    bot.send_message(admin_id, f"🚨 Withdrawal Request:\nUser: {message.chat.id}\nAmount: ₹{user['balance']}\nUPI: {upi_id}")

    users.update_one({"user_id": message.chat.id}, {"$set": {"balance": 0}})
    bot.send_message(message.chat.id, "✅ Withdrawal request sent to admin!")

bot.polling()
