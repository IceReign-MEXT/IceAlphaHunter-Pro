import telebot
from telebot import types
import os, threading, json, random
from flask import Flask
import firebase_admin
from firebase_admin import credentials, firestore

# --- CONFIG ---
TOKEN = os.environ.get("BOT_TOKEN", "7714757245:AAHJIbMRwg8M6tiUBROAX4NAuwvKxXgDkNc")
CHANNEL_ID = -1002384609234
VAULT = "0x20d2708acd360cd0fd416766802e055295470fc1"
APP_ID = "mex-war-system"

bot = telebot.TeleBot(TOKEN, threaded=False)

# --- DATABASE ---
db = None
try:
    creds_raw = os.environ.get("FIREBASE_SERVICE_ACCOUNT")
    if creds_raw:
        creds_dict = json.loads(creds_raw)
        if "private_key" in creds_dict:
            creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
        cred = credentials.Certificate(creds_dict)
        firebase_admin.initialize_app(cred)
        db = firestore.client()
except Exception as e:
    print(f"DB_ERR: {e}")

def broadcast(msg):
    try: bot.send_message(CHANNEL_ID, msg, parse_mode="Markdown")
    except: pass

# --- COMMANDS ---
@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('🚀 EXECUTE_SNIPE', '🛡️ AUDIT_CA', '💰 WALLET', '🔑 ACTIVATE')
    bot.send_message(message.chat.id, "⚔️ *ICE_ALPHA_PRO V2.5*\nNode Status: *ENCRYPTED*\nRevenue Tax: *1.0% ACTIVE*", reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(func=lambda m: True)
def handle(message):
    uid = message.from_user.id
    if message.text == '🚀 EXECUTE_SNIPE':
        broadcast(f"🎯 *TARGETING:* Node `{uid}` scanning liquidity...")
        bot.reply_to(message, "🎯 *TARGET_MODE:* Paste CA. 1% Tax routing is active.")
    elif message.text == '🛡️ AUDIT_CA':
        bot.reply_to(message, "🛡️ *SCANNER:* Send CA for Rug-Check.")

# --- SERVER ---
app = Flask(__name__)
@app.route('/')
def home(): return "RUNNING", 200

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000))), daemon=True).start()
    broadcast("🚀 *[SYSTEM_BOOT]* Engine is ONLINE. 1% Tax active.")
    bot.polling(none_stop=True)

