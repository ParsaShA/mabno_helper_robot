import telebot
import json
import os
from dotenv import load_dotenv
load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')


telebot.apihelper.proxy = {
    'https': 'socks5h://127.0.0.1:10808'
}

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
BOT_USERNAME = bot.get_me().username.lower()

TASKS_FILE = "tasks.json"

def load_tasks():
    if os.path.exists(TASKS_FILE):
        with open(TASKS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_tasks(tasks):
    with open(TASKS_FILE, "w", encoding="utf-8") as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2)

tasks = load_tasks()
user_state = {}
WAITING_FOR_DESCRIPTION = "waiting_for_description"
WAITING_FOR_DATE = "waiting_for_date"


def is_mentioned_or_private(message):
    if message.chat.type == "private":
        return True
    if message.chat.type in ['group', 'supergroup']:
        text = (message.text or "").lower()
        return f"@{BOT_USERNAME}" in text
    return False

@bot.message_handler(commands=['start', 'add', 'history', 'delete'])
def handle_commands(message):
    if not is_mentioned_or_private(message):
        return

    command = message.text.split()[0].lower().lstrip('/').split('@')[0]

    if command == 'start':
        bot.reply_to(message, (
            "سلام مبنو 😄\n"
            "دستورات من:\n"
            "/add ➕ افزودن تسک جدید\n"
            "/history 📋 مشاهده تسک‌ها\n"
            "/delete ❌ حذف تسک"
        ))

    elif command == 'add':
        chat_id = str(message.chat.id)
        user_state[chat_id] = WAITING_FOR_DESCRIPTION
        bot.reply_to(message, "لطفاً توضیح تسک را بنویس:")

    elif command == 'history':
        chat_id = str(message.chat.id)
        if chat_id not in tasks or not tasks[chat_id]:
            bot.reply_to(message, "هیچ تسکی ثبت نشده.")
            return
        text = "لیست تسک‌ها:\n\n"
        for i, t in enumerate(tasks[chat_id], 1):
            text += f"{i}. {t['description']} — {t['date']}\n"
        bot.reply_to(message, text)

    elif command == 'delete':
        chat_id = str(message.chat.id)
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            bot.reply_to(message, "برای حذف بنویس:\n/delete <متن>")
            return
        query = parts[1].strip()
        if chat_id not in tasks or not tasks[chat_id]:
            bot.reply_to(message, "هیچ تسکی برای حذف نیست.")
            return
        removed = [t for t in tasks[chat_id] if query in t['description'] or query in t['date']]
        if not removed:
            bot.reply_to(message, "تسکی پیدا نشد.")
            return
        tasks[chat_id] = [t for t in tasks[chat_id] if t not in removed]
        save_tasks(tasks)
        removed_text = "\n".join([f"{t['description']} — {t['date']}" for t in removed])
        bot.reply_to(message, f"تسک(های) زیر حذف شد:\n\n{removed_text}")

@bot.message_handler(func=lambda m: user_state.get(str(m.chat.id)) == WAITING_FOR_DESCRIPTION)
def get_description(message):
    if not is_mentioned_or_private(message):
        return
    chat_id = str(message.chat.id)
    user_state[chat_id] = WAITING_FOR_DATE
    user_state[f"{chat_id}_desc"] = message.text
    bot.reply_to(message, "حالا تاریخ ددلاین را بنویس (مثلاً ۱۴۰۴/۱۱/۱۵):")



@bot.message_handler(func=lambda m: user_state.get(str(m.chat.id)) == WAITING_FOR_DATE)
def get_date(message):
    if not is_mentioned_or_private(message):
        return
    chat_id = str(message.chat.id)
    desc = user_state.get(f"{chat_id}_desc", "بدون توضیح")
    date = message.text
    if chat_id not in tasks:
        tasks[chat_id] = []
    tasks[chat_id].append({"description": desc, "date": date})
    save_tasks(tasks)
    bot.reply_to(message, f"تسک اضافه شد!\n\n<b>{desc}</b>\n<b>{date}</b>")
    user_state.pop(chat_id, None)
    user_state.pop(f"{chat_id}_desc", None)


@bot.message_handler(func=lambda m: m.chat.type in ['group', 'supergroup'] and
                    f"@{BOT_USERNAME}" in (m.text or "").lower() and
                    not m.text.strip().startswith('/'))
def handle_mention_only(message):
    bot.reply_to(message, (
        "سلام! من ربات مدیریت تسک هستم\n"
        "برای استفاده در گروه، دستورات رو با منشن بزن:\n\n"
        f"• <code>@{bot.get_me().username} /add</code> ➕ افزودن تسک\n"
        f"• <code>@{bot.get_me().username} /history</code> 📋 لیست تسک‌ها\n"
        f"• <code>@{bot.get_me().username} /delete متن</code> ❌ حذف تسک\n\n"
        "یا در چت خصوصی بدون منشن استفاده کن."
    ), parse_mode="HTML")



@bot.message_handler(func=lambda m: m.chat.type == "private")
def private_fallback(message):
    if message.text.startswith('/'):
        return
    bot.reply_to(message, "برای شروع از /add استفاده کن")


try:
    bot.infinity_polling(none_stop=True, interval=0, timeout=20)
except Exception as e:
    print(f"خطا: {e}")
    import time
    time.sleep(5)