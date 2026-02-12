import os
import telebot
import sqlite3
from telebot.types import ReplyKeyboardMarkup
from flask import Flask
import threading

TOKEN = os.getenv("8447058713:AAG7jkj0DyFRO09q82tfBnulaUhZUEObAvc")
ADMIN_ID = int(os.getenv("7787109849"))  # O'zingizning Telegram ID

bot = telebot.TeleBot(TOKEN)

# ===== DATABASE =====
conn = sqlite3.connect("kino_bot.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("CREATE TABLE IF NOT EXISTS movies (code TEXT PRIMARY KEY, file_id TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)")
cursor.execute("CREATE TABLE IF NOT EXISTS channels (username TEXT PRIMARY KEY)")
conn.commit()

# ===== ADMIN MENU =====
def admin_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🎬 Kino qo'shish")
    markup.add("❌ Kino o'chirish", "📊 Kino soni")
    markup.add("👥 Foydalanuvchilar soni")
    markup.add("➕ Homiy qo'shish", "➖ Homiy o'chirish")
    markup.add("📋 Homiylar ro'yxati")
    return markup

# ===== OBUNA TEKSHIRISH =====
def check_all_subscriptions(user_id):
    cursor.execute("SELECT username FROM channels")
    channels = cursor.fetchall()
    not_joined = []

    for ch in channels:
        channel = ch[0]
        try:
            member = bot.get_chat_member(channel, user_id)
            if member.status not in ["member", "creator", "administrator"]:
                not_joined.append(channel)
        except:
            not_joined.append(channel)

    return not_joined

# ===== START =====
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()

    if user_id == ADMIN_ID:
        bot.send_message(message.chat.id, "Admin panelga xush kelibsiz", reply_markup=admin_menu())
        return

    not_joined = check_all_subscriptions(user_id)
    if not_joined:
        markup = ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("✅ Tekshirish")
        bot.send_message(
            message.chat.id,
            "❌ Kinoni olish uchun quyidagi kanallarga obuna bo‘ling:\n\n" + "\n".join(not_joined),
            reply_markup=markup
        )
    else:
        bot.send_message(message.chat.id, "🎬 Kino kodini yuboring:")

# ===== TEKSHIRISH TUGMASI =====
@bot.message_handler(func=lambda m: m.text == "✅ Tekshirish")
def recheck(message):
    not_joined = check_all_subscriptions(message.from_user.id)
    if not_joined:
        markup = ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("✅ Tekshirish")
        bot.send_message(message.chat.id,
                         "❌ Hali ham obuna emassiz:\n\n" + "\n".join(not_joined),
                         reply_markup=markup)
    else:
        bot.send_message(message.chat.id, "✅ Obuna tasdiqlandi! Endi kino kodini yuboring.")

# ===== ADMIN: ADD MOVIE =====
@bot.message_handler(func=lambda m: m.text == "🎬 Kino qo'shish" and m.from_user.id == ADMIN_ID)
def add_movie(message):
    msg = bot.send_message(message.chat.id, "Kinoni video shaklida yuboring:")
    bot.register_next_step_handler(msg, get_video)

def get_video(message):
    if not message.video:
        msg = bot.send_message(message.chat.id, "❗ Videoni yuboring:")
        bot.register_next_step_handler(msg, get_video)
        return

    file_id = message.video.file_id
    msg = bot.send_message(message.chat.id, "Kino kodini yozing:")
    bot.register_next_step_handler(msg, save_code, file_id)

def save_code(message, file_id):
    code = message.text.strip()
    try:
        cursor.execute("INSERT INTO movies VALUES (?, ?)", (code, file_id))
        conn.commit()
        bot.send_message(message.chat.id, "✅ Kino saqlandi", reply_markup=admin_menu())
    except:
        bot.send_message(message.chat.id, "❌ Bu kod mavjud", reply_markup=admin_menu())

# ===== DELETE MOVIE =====
@bot.message_handler(func=lambda m: m.text == "❌ Kino o'chirish" and m.from_user.id == ADMIN_ID)
def delete_movie(message):
    msg = bot.send_message(message.chat.id, "Kino kodini yuboring:")
    bot.register_next_step_handler(msg, delete_code)

def delete_code(message):
    cursor.execute("DELETE FROM movies WHERE code=?", (message.text.strip(),))
    conn.commit()
    bot.send_message(message.chat.id, "✅ O‘chirildi", reply_markup=admin_menu())

# ===== MOVIE COUNT =====
@bot.message_handler(func=lambda m: m.text == "📊 Kino soni" and m.from_user.id == ADMIN_ID)
def movie_count(message):
    cursor.execute("SELECT COUNT(*) FROM movies")
    bot.send_message(message.chat.id, f"🎬 Kinolar soni: {cursor.fetchone()[0]}")

# ===== USERS COUNT =====
@bot.message_handler(func=lambda m: m.text == "👥 Foydalanuvchilar soni" and m.from_user.id == ADMIN_ID)
def users_count(message):
    cursor.execute("SELECT COUNT(*) FROM users")
    bot.send_message(message.chat.id, f"👥 Foydalanuvchilar: {cursor.fetchone()[0]}")

# ===== ADD SPONSOR =====
@bot.message_handler(func=lambda m: m.text == "➕ Homiy qo'shish" and m.from_user.id == ADMIN_ID)
def add_channel(message):
    msg = bot.send_message(message.chat.id, "Kanal username yuboring (@kanal):")
    bot.register_next_step_handler(msg, save_channel)

def save_channel(message):
    username = message.text.strip()
    if not username.startswith("@"):
        bot.send_message(message.chat.id, "❌ @ bilan boshlanishi kerak")
        return
    try:
        cursor.execute("INSERT INTO channels VALUES (?)", (username,))
        conn.commit()
        bot.send_message(message.chat.id, "✅ Homiy qo‘shildi", reply_markup=admin_menu())
    except:
        bot.send_message(message.chat.id, "❌ Allaqachon mavjud", reply_markup=admin_menu())

# ===== REMOVE SPONSOR =====
@bot.message_handler(func=lambda m: m.text == "➖ Homiy o'chirish" and m.from_user.id == ADMIN_ID)
def remove_channel(message):
    msg = bot.send_message(message.chat.id, "O‘chiriladigan kanal username:")
    bot.register_next_step_handler(msg, delete_channel)

def delete_channel(message):
    cursor.execute("DELETE FROM channels WHERE username=?", (message.text.strip(),))
    conn.commit()
    bot.send_message(message.chat.id, "✅ O‘chirildi", reply_markup=admin_menu())

# ===== LIST SPONSORS =====
@bot.message_handler(func=lambda m: m.text == "📋 Homiylar ro'yxati" and m.from_user.id == ADMIN_ID)
def list_channels(message):
    cursor.execute("SELECT username FROM channels")
    channels = cursor.fetchall()
    text = "\n".join([c[0] for c in channels]) if channels else "Yo‘q"
    bot.send_message(message.chat.id, "📢 Homiy kanallar:\n" + text)

# ===== USER MOVIE REQUEST =====
@bot.message_handler(func=lambda m: True)
def send_movie(message):
    if message.from_user.id == ADMIN_ID:
        return

    not_joined = check_all_subscriptions(message.from_user.id)
    if not_joined:
        markup = ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("✅ Tekshirish")
        bot.send_message(message.chat.id,
                         "❌ Obuna bo‘ling:\n" + "\n".join(not_joined),
                         reply_markup=markup)
        return

    cursor.execute("SELECT file_id FROM movies WHERE code=?", (message.text.strip(),))
    movie = cursor.fetchone()
    if movie:
        bot.send_video(message.chat.id, movie[0])
    else:
        bot.send_message(message.chat.id, "❌ Bunday kod topilmadi")

app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running"

def run_bot():
    print("Bot ishga tushdi...")
    bot.infinity_polling()

threading.Thread(target=run_bot).start()

if __name__ =="__main__":
    port = int(os.environ.get("PORT", 10000))

    app.run(host="0.0.0.0", port=port)

