import logging, json, pytz, datetime, schedule, time, random, requests
from threading import Thread
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, filters, ContextTypes

(THEME_SELECTION, NAME, BIRTHDAY, CITY, PROFESSION, SLEEP, GOALS, HOBBIES, MORNING_PRODUCTIVITY, NOTIFY_TIME) = range(10)

TOPICS = [
    "💰 Криптовалюта","🧙 Гороскоп","☀️ Погода",
    "🧠 Цитата дня","💼 Продуктивность","🍽 Совет по питанию",
    "🎬 Рекомендация дня","🎉 Личные напоминания","✅ To‑do задачи"
]

users, reminders, todos = {}, {}, {}
logging.basicConfig(level=logging.INFO)

TOKEN = "7855248264:AAEvDeAi-3lC5hbsI3y_H8qYG22aitUzT88"
OWM_KEY = "bb4019aa070450b7031cee639418b585"

def get_crypto(): ...
def get_weather(city): ...
def get_generated_horoscope(sign): ...
def get_quote(): ...
def get_productivity(): ...
def get_food_advice(): ...
def get_recommendation(): ...
def get_zodiac(day, month): ...
def load_users():
    global users
    try:
        with open("users.json","r") as f: users = json.load(f)
    except: users = {}
def save_users():
    with open("users.json","w") as f: json.dump(users, f, indent=2)

async def send_personalized(uid, context): ...

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['interests'] = []
    await update.message.reply_text("Привет! Выбери интересующие тебя темы:", reply_markup=generate_topic_markup([]))
    return THEME_SELECTION

def generate_topic_markup(selected):
    keyboard = [[InlineKeyboardButton(t + (" ✅" if t in selected else ""), callback_data=t)] for t in TOPICS]
    keyboard.append([InlineKeyboardButton("✅ Готово", callback_data="done")])
    return InlineKeyboardMarkup(keyboard)

async def theme_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    choice = query.data
    if choice == "done":
        if not context.user_data["interests"]:
            await query.edit_message_reply_markup(reply_markup=generate_topic_markup([]))
            await query.edit_message_text("Пожалуйста, выбери хотя бы одну тему.")
            return THEME_SELECTION
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text("Как тебя зовут?", reply_markup=skip_markup())
        return NAME
    # добавление/удаление выбора
    if choice in context.user_data["interests"]:
        context.user_data["interests"].remove(choice)
    else:
        context.user_data["interests"].append(choice)
    await query.edit_message_reply_markup(reply_markup=generate_topic_markup(context.user_data["interests"]))
    return THEME_SELECTION

def skip_markup():
    return ReplyKeyboardMarkup([["Пропустить"]], resize_keyboard=True, one_time_keyboard=True)

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE): ...
async def get_birthday(update: Update, context: ContextTypes.DEFAULT_TYPE): ...
async def get_city(update: Update, context: ContextTypes.DEFAULT_TYPE): ...
async def get_profession(update: Update, context: ContextTypes.DEFAULT_TYPE): ...
async def get_sleep(update: Update, context: ContextTypes.DEFAULT_TYPE): ...
async def get_goals(update: Update, context: ContextTypes.DEFAULT_TYPE): ...
async def get_hobbies(update: Update, context: ContextTypes.DEFAULT_TYPE): ...
async def get_productivity_level(update: Update, context: ContextTypes.DEFAULT_TYPE): ...
async def get_notify_time(update: Update, context: ContextTypes.DEFAULT_TYPE): ...

async def test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_personalized(update.effective_user.id, context)

if __name__ == "__main__":
    load_users()
    app = ApplicationBuilder().token(TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            THEME_SELECTION: [CallbackQueryHandler(theme_selection)],
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            BIRTHDAY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_birthday)],
            CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_city)],
            PROFESSION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_profession)],
            SLEEP: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_sleep)],
            GOALS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_goals)],
            HOBBIES: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_hobbies)],
            MORNING_PRODUCTIVITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_productivity_level)],
            NOTIFY_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_notify_time)],
        },
        fallbacks=[]
    )

    app.add_handler(conv)
    app.add_handler(CommandHandler("test", test))

    def run_scheduler():
        while True:
            schedule.run_pending()
            time.sleep(10)

    def schedule_job():
        for uid in users:
            app.create_task(send_personalized(uid, app))

    schedule.every().day.at("08:00").do(schedule_job)
    Thread(target=run_scheduler, daemon=True).start()

    print("Бот запущен")
    app.run_polling()