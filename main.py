import telebot
import os
import sqlite3
from dotenv import load_dotenv
from datetime import datetime
from telebot import types


load_dotenv()
API_TOKEN = os.getenv('BOT_TOKEN')

ALLOWED_USER_IDS = ['x1','x2']
PROXY = None 

user_states = {}
DATABASE_NAME = 'task_manager.db'

if PROXY:
    telebot.apihelper.proxy = {'https': PROXY}
    print("Proxy set up.")

bot = telebot.TeleBot(API_TOKEN)



def init_db():
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT NOT NULL,
            assigned_to TEXT,
            due_date TEXT,
            creator_id INTEGER,
            is_completed INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()
    print("Database initialized.")


def db_query(query, params=(), fetch_one=False, commit=False):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute(query, params)

        if commit:
            conn.commit()
            conn.close()
            return None

        result = cursor.fetchone() if fetch_one else cursor.fetchall()
        return result
    except Exception as e:
        print(f"Database Error: {e}")
        return None
    finally:
        conn.close()



def authorized_only(func):

    def wrapper(message):
        if message.from_user.id not in ALLOWED_USER_IDS:
            # فقط در چت‌های خصوصی پیام عدم دسترسی ارسال شود.
            if message.chat.type == 'private':
                bot.send_message(
                    message.chat.id,
                    "⛔️ **شما مجاز به استفاده از این ربات نیستید.**",
                    parse_mode="Markdown"
                )
            return
        return func(message)

    return wrapper


def get_main_menu():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    item_add = types.KeyboardButton("➕ افزودن (Add)")
    item_delete = types.KeyboardButton("❌ حذف (Delete)")
    item_update = types.KeyboardButton("✍️ به‌روزرسانی (Update)")
    item_history = types.KeyboardButton("📜 تاریخچه (History)")
    markup.add(item_add, item_delete, item_update, item_history)
    return markup


@bot.message_handler(commands=['start'])
@authorized_only
def send_welcome(message):
    greeting = "Hello mabno, I'm task manager bot. What can I do for you?"
    bot.send_message(
        message.chat.id,
        greeting,
        reply_markup=get_main_menu()
    )


STATE_ADD_DESCRIPTION = 1
STATE_ADD_PERSON = 2
STATE_ADD_DATE = 3


@bot.message_handler(func=lambda message: message.text in ["➕ افزودن (Add)", "Add"])
@authorized_only
def start_add_task(message):
    user_states[message.from_user.id] = {'step': STATE_ADD_DESCRIPTION, 'data': {}}
    msg = bot.send_message(
        message.chat.id,
        "Please enter the **description** of the task.",
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, get_task_description)


def get_task_description(message):
    user_id = message.from_user.id
    if message.text in ["➕ افزودن (Add)", "❌ حذف (Delete)", "✍️ به‌روزرسانی (Update)", "📜 تاریخچه (History)"]:
        bot.send_message(message.chat.id, "عملیات فعلی لغو شد. لطفا دوباره شروع کنید.")
        del user_states[user_id]
        return

    user_states[user_id]['data']['description'] = message.text
    user_states[user_id]['step'] = STATE_ADD_PERSON

    msg = bot.send_message(message.chat.id, "Who is the task **assigned to**?", parse_mode="Markdown")
    bot.register_next_step_handler(msg, get_task_person)


def get_task_person(message):
    user_id = message.from_user.id
    if message.text in ["➕ افزودن (Add)", "❌ حذف (Delete)", "✍️ به‌روزرسانی (Update)", "📜 تاریخچه (History)"]:
        bot.send_message(message.chat.id, "عملیات فعلی لغو شد. لطفا دوباره شروع کنید.")
        del user_states[user_id]
        return

    user_states[user_id]['data']['assigned_to'] = message.text
    user_states[user_id]['step'] = STATE_ADD_DATE

    msg = bot.send_message(message.chat.id, "What is the **due date**? (Format: YYYY-MM-DD)", parse_mode="Markdown")
    bot.register_next_step_handler(msg, save_task)


def save_task(message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    if message.text in ["➕ افزودن (Add)", "❌ حذف (Delete)", "✍️ به‌روزرسانی (Update)", "📜 تاریخچه (History)"]:
        bot.send_message(message.chat.id, "عملیات فعلی لغو شد. لطفا دوباره شروع کنید.")
        del user_states[user_id]
        return

    due_date_str = message.text.strip()

    try:
        datetime.strptime(due_date_str, '%Y-%m-%d')
    except ValueError:
        msg = bot.send_message(
            chat_id,
            "⚠️ **فرمت تاریخ نامعتبر است.** لطفا تاریخ را با فرمت **YYYY-MM-DD** مجدداً ارسال کنید."
        )
        return bot.register_next_step_handler(msg, save_task)

    data = user_states[user_id]['data']
    description = data['description']
    assigned_to = data['assigned_to']

    db_query(
        "INSERT INTO tasks (description, assigned_to, due_date, creator_id) VALUES (?, ?, ?, ?)",
        (description, assigned_to, due_date_str, user_id),
        commit=True
    )

    bot.send_message(
        chat_id,
        "✅ **وظیفه با موفقیت اضافه شد!**\n\n**توضیحات:** {}\n**مسئول:** {}\n**تاریخ سررسید:** {}".format(
            description, assigned_to, due_date_str
        ),
        parse_mode="Markdown",
        reply_markup=get_main_menu()
    )
    del user_states[user_id]



@bot.message_handler(func=lambda message: message.text in ["❌ حذف (Delete)", "Delete"])
@authorized_only
def start_delete_task(message):
    msg = bot.send_message(
        message.chat.id,
        "Please enter a few **keywords** from the task description to search for the task.",
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, search_and_delete_task)


def search_and_delete_task(message):
    chat_id = message.chat.id
    keywords = message.text

    tasks = db_query(
        "SELECT id, description, due_date FROM tasks WHERE description LIKE ? AND is_completed = 0 ORDER BY due_date",
        (f"%{keywords}%",)
    )

    if not tasks:
        bot.send_message(chat_id, "🔍 **هیچ وظیفه ناتمامی با این کلمات کلیدی پیدا نشد.**", parse_mode="Markdown")
        return

    markup = types.InlineKeyboardMarkup()
    response_text = "🗑️ **وظیفه مورد نظر برای حذف را انتخاب کنید:**\n\n"

    for task_id, desc, date in tasks:
        callback_data = f'delete_{task_id}'
        button_text = f"❌ {desc[:30]}... (تا {date})"
        markup.add(types.InlineKeyboardButton(button_text, callback_data=callback_data))

    bot.send_message(chat_id, response_text, reply_markup=markup, parse_mode="Markdown")


@bot.callback_query_handler(func=lambda call: call.data.startswith('delete_'))
def callback_delete_task(call):
    try:
        task_id = int(call.data.split('_')[1])
    except:
        bot.answer_callback_query(call.id, "خطا در پردازش شناسه وظیفه.")
        return

    db_query("DELETE FROM tasks WHERE id = ?", (task_id,), commit=True)

    bot.edit_message_text(
        "✅ **وظیفه با موفقیت حذف شد!** (ID: {})".format(task_id),
        call.message.chat.id,
        call.message.message_id,
        parse_mode="Markdown"
    )
    bot.answer_callback_query(call.id, "وظیفه حذف شد.")


STATE_UPDATE_NEW_DESCRIPTION = 5


@bot.message_handler(func=lambda message: message.text in ["✍️ به‌روزرسانی (Update)", "Update"])
@authorized_only
def start_update_task(message):
    msg = bot.send_message(
        message.chat.id,
        "Please enter some words of the description for **searching and updating**.",
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, search_and_select_update)


def search_and_select_update(message):
    chat_id = message.chat.id
    keywords = message.text

    tasks = db_query(
        "SELECT id, description, due_date FROM tasks WHERE description LIKE ? ORDER BY due_date",
        (f"%{keywords}%",)
    )

    if not tasks:
        bot.send_message(chat_id, "🔍 **هیچ وظیفه‌ای با این کلمات کلیدی پیدا نشد.**", parse_mode="Markdown")
        return

    markup = types.InlineKeyboardMarkup()
    response_text = "🔄 **وظیفه مورد نظر برای به‌روزرسانی را انتخاب کنید:**\n\n"

    for task_id, desc, date in tasks:
        callback_data = f'update_{task_id}'
        button_text = f"✍️ {desc[:30]}... (تا {date})"
        markup.add(types.InlineKeyboardButton(button_text, callback_data=callback_data))

    bot.send_message(chat_id, response_text, reply_markup=markup, parse_mode="Markdown")


@bot.callback_query_handler(func=lambda call: call.data.startswith('update_'))
def callback_start_update(call):
    chat_id = call.message.chat.id
    user_id = call.from_user.id

    try:
        task_id = int(call.data.split('_')[1])
        user_states[user_id] = {'step': STATE_UPDATE_NEW_DESCRIPTION, 'task_id': task_id}
    except:
        bot.answer_callback_query(call.id, "خطا در پردازش شناسه وظیفه.")
        return

    bot.edit_message_text(
        f"⏳ **وظیفه انتخاب شد.** (ID: {task_id})\n\n**لطفاً توضیحات جدید را وارد یا Paste کنید.** (فیلدهای دیگر ثابت می‌مانند.)",
        call.message.chat.id,
        call.message.message_id,
        parse_mode="Markdown"
    )

    bot.register_next_step_handler(call.message, final_update_task)

    bot.answer_callback_query(call.id, "وظیفه برای به‌روزرسانی انتخاب شد.")


def final_update_task(message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    if user_id not in user_states or user_states[user_id]['step'] != STATE_UPDATE_NEW_DESCRIPTION:
        return

    task_id = user_states[user_id]['task_id']
    new_description = message.text

    db_query(
        "UPDATE tasks SET description = ? WHERE id = ?",
        (new_description, task_id),
        commit=True
    )

    bot.send_message(
        chat_id,
        "✅ **توضیحات وظیفه با موفقیت به‌روزرسانی شد!**\n\n**ID:** {}\n**توضیحات جدید:** {}".format(
            task_id, new_description
        ),
        parse_mode="Markdown",
        reply_markup=get_main_menu()
    )

    del user_states[user_id]



@bot.message_handler(func=lambda message: message.text in ["📜 تاریخچه (History)", "History"])
@authorized_only
def show_history(message):
    """نمایش کامل تاریخچه وظایف."""
    tasks = db_query(
        "SELECT id, description, assigned_to, due_date, is_completed FROM tasks ORDER BY id DESC"
    )

    if not tasks:
        bot.send_message(message.chat.id, "📚 **تاریخچه وظایف شما خالی است.**")
        return

    history_text = "📜 **تاریخچه کامل وظایف:**\n\n"

    for task_id, desc, assigned, date, completed in tasks:
        status = "✅ انجام‌شده" if completed else "⏳ ناتمام"
        entry = (
            f"**ID:** `{task_id}`\n"
            f"**وضعیت:** {status}\n"
            f"**توضیحات:** {desc}\n"
            f"**مسئول:** {assigned}\n"
            f"**سررسید:** {date}\n"
            f"------\n"
        )

        # مدیریت محدودیت طول پیام تلگرام
        if len(history_text) + len(entry) > 4000:
            bot.send_message(message.chat.id, history_text, parse_mode="Markdown")
            history_text = entry
        else:
            history_text += entry

    if history_text:
        bot.send_message(message.chat.id, history_text, parse_mode="Markdown")


@bot.message_handler(content_types=['text'], func=lambda message: message.chat.type in ['group',
                                                                                        'supergroup'] and f'@{bot.get_me().username}' in message.text)
@authorized_only
def handle_group_mentions(message):
    bot_username = bot.get_me().username
    try:
        text_after_mention = message.text.split(f'@{bot_username}', 1)[1].strip()
    except IndexError:
        text_after_mention = ""

    command_map = {
        "add": start_add_task, "افزودن": start_add_task,
        "delete": start_delete_task, "حذف": start_delete_task,
        "update": start_update_task, "به‌روزرسانی": start_update_task,
        "history": show_history, "تاریخچه": show_history,
    }

    if not text_after_mention or any(cmd in text_after_mention.lower() for cmd in ["دستورات", "سلام", "شروع"]):
        greeting = "Hello mabno, I'm task manager bot. What can I do for you? \n\n**Commands:** Add, Delete, Update, History"
        bot.send_message(message.chat.id, greeting, parse_mode="Markdown")
        return

    for cmd_key, handler in command_map.items():
        if text_after_mention.lower().startswith(cmd_key):
            message.text = cmd_key
            handler(message)
            return

if __name__ == '__main__':
    init_db()
    print("Bot is starting...")
    try:
        bot.infinity_polling()
    except Exception as e:
        print(f"An error occurred: {e}")

