import logging, json, pytz, datetime, schedule, time, random, requests
from threading import Thread
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ConversationHandler, filters, ContextTypes

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
    await update.message.reply_text(
        "Привет! Давай сначала выберем, какие темы тебе интересны.\n"
        "Введи через запятую или пробел несколько тем из списка:\n"
        + ", ".join([t.split()[1] for t in TOPICS])
    )
    return THEME_SELECTION

async def get_themes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    selected = update.message.text.replace("\n", ",").replace(";", ",")
    chosen = [topic.strip() for topic in selected.split(",") if topic.strip() in [t.split()[1] for t in TOPICS]]
    full_chosen = [t for t in TOPICS if t.split()[1] in chosen]
    if not full_chosen:
        await update.message.reply_text("Не удалось распознать интересы. Попробуй ещё раз:")
        return THEME_SELECTION
    context.user_data['interests'] = full_chosen
    await update.message.reply_text("Как тебя зовут?", reply_markup=skip_markup())
    return NAME

def skip_markup():
    return ReplyKeyboardMarkup([["Пропустить"]], resize_keyboard=True, one_time_keyboard=True)

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text != "Пропустить":
        context.user_data["name"] = text
    else:
        context.user_data["name"] = ""
    await update.message.reply_text("Когда у тебя день рождения? (ДД.ММ)", reply_markup=skip_markup())
    return BIRTHDAY

async def get_birthday(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text != "Пропустить":
        try:
            day, month = map(int, text.split("."))
            zodiac = get_zodiac(day, month)
            context.user_data["zodiac"] = zodiac
        except:
            await update.message.reply_text("Формат даты неверный. Пример: 24.09")
            return BIRTHDAY
    else:
        context.user_data["zodiac"] = ""
    await update.message.reply_text("В каком ты городе?", reply_markup=skip_markup())
    return CITY

async def get_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    context.user_data["city"] = text if text != "Пропустить" else ""
    await update.message.reply_text("Чем ты занимаешься? (профессия/деятельность)", reply_markup=skip_markup())
    return PROFESSION

async def get_profession(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["profession"] = update.message.text if update.message.text != "Пропустить" else ""
    await update.message.reply_text("Сколько ты обычно спишь в сутки (в часах)?", reply_markup=skip_markup())
    return SLEEP

async def get_sleep(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["sleep"] = update.message.text if update.message.text != "Пропустить" else ""
    await update.message.reply_text("Какие цели ставишь перед собой на этот месяц?", reply_markup=skip_markup())
    return GOALS

async def get_goals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["goals"] = update.message.text if update.message.text != "Пропустить" else ""
    await update.message.reply_text("Чем ты любишь заниматься в свободное время?", reply_markup=skip_markup())
    return HOBBIES

async def get_hobbies(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["hobbies"] = update.message.text if update.message.text != "Пропустить" else ""
    await update.message.reply_text("Как ты оцениваешь свою продуктивность утром? (низкая / средняя / высокая)", reply_markup=skip_markup())
    return MORNING_PRODUCTIVITY

async def get_productivity_level(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["morning"] = update.message.text if update.message.text != "Пропустить" else ""
    await update.message.reply_text("Во сколько тебе удобно получать утренние сообщения? (например, 08:00)", reply_markup=skip_markup())
    return NOTIFY_TIME

async def get_notify_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["notify"] = update.message.text if update.message.text != "Пропустить" else "08:00"
    uid = str(update.effective_user.id)
    users[uid] = {
        "name": context.user_data.get("name", ""),
        "zodiac": context.user_data.get("zodiac", ""),
        "city": context.user_data.get("city", ""),
        "interests": context.user_data.get("interests", []),
        "profession": context.user_data.get("profession", ""),
        "sleep": context.user_data.get("sleep", ""),
        "goals": context.user_data.get("goals", ""),
        "hobbies": context.user_data.get("hobbies", ""),
        "morning": context.user_data.get("morning", ""),
        "notify": context.user_data.get("notify", "08:00")
    }
    save_users()
    await update.message.reply_text("Спасибо! Я буду присылать тебе персональные советы каждый день.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

async def test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_personalized(update.effective_user.id, context)

if __name__ == "__main__":
    load_users()
    app = ApplicationBuilder().token(TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            THEME_SELECTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_themes)],
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
