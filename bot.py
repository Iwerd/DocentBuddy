import logging
import json
import pytz
import datetime
import schedule
import time
import random
from threading import Thread
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ConversationHandler, filters, ContextTypes
)

NAME, BIRTHDAY, CITY, TIME, INTERESTS = range(5)

TOPICS = [
    "💰 Криптовалюта",
    "🧙 Гороскоп",
    "🕹 Игры",
    "💄 Красота",
    "🧘‍♀️ Здоровье",
    "☀️ Погода",
    "🧠 Факт дня",
    "💼 Продуктивность",
    "🧠 Цитата дня",
    "💹 Курс валют / крипты",
    "🍽 Совет по питанию",
    "🎬 Рекомендация дня",
    "🎉 Личные напоминания",
    "✅ To-do задачи"
]

users = {}
reminders = {}
todos = {}

logging.basicConfig(level=logging.INFO)

def load_users():
    global users
    try:
        with open("users.json", "r") as f:
            users = json.load(f)
    except:
        users = {}

def save_users():
    with open("users.json", "w") as f:
        json.dump(users, f, indent=2)

def get_zodiac(day, month):
    zodiac = [
        (20, "Козерог"), (19, "Водолей"), (20, "Рыбы"),
        (20, "Овен"), (21, "Телец"), (21, "Близнецы"),
        (23, "Рак"), (23, "Лев"), (23, "Дева"),
        (23, "Весы"), (23, "Скорпион"), (22, "Стрелец"),
        (31, "Козерог")
    ]
    if day < zodiac[month - 1][0]:
        return zodiac[month - 1][1]
    return zodiac[month][1]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Как тебя зовут?")
    return NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text
    await update.message.reply_text("Когда твой день рождения? (ДД.ММ.ГГГГ)")
    return BIRTHDAY

async def get_birthday(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        bday = datetime.datetime.strptime(update.message.text, "%d.%m.%Y")
        context.user_data["birthday"] = update.message.text
        context.user_data["zodiac"] = get_zodiac(bday.day, bday.month)
        await update.message.reply_text("В каком городе ты живешь?")
        return CITY
    except:
        await update.message.reply_text("Пожалуйста, используй формат ДД.ММ.ГГГГ")
        return BIRTHDAY

async def get_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["city"] = update.message.text
    await update.message.reply_text("Во сколько тебе удобно получать сообщения? (например: 08:00)")
    return TIME

async def get_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["time"] = update.message.text
    return await ask_interests(update, context)

async def ask_interests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[topic] for topic in TOPICS] + [["✅ Готово"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
    context.user_data["interests"] = []
    await update.message.reply_text("Выбери, что тебе интересно (можно несколько). Когда закончишь — нажми «Готово».", reply_markup=reply_markup)
    return INTERESTS

async def collect_interests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    choice = update.message.text
    if choice == "✅ Готово":
        user_id = str(update.message.chat_id)
        users[user_id] = context.user_data
        save_users()
        await update.message.reply_text(f"Спасибо! С завтрашнего дня я буду присылать тебе полезную информацию по темам: {', '.join(context.user_data['interests'])}.", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    elif choice in TOPICS:
        if choice not in context.user_data["interests"]:
            context.user_data["interests"].append(choice)
        await update.message.reply_text(f"Добавлено: {choice}")
    return INTERESTS

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Окей, если что — напиши /start.")
    return ConversationHandler.END

async def add_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.chat_id)
    task = " ".join(context.args)
    if user_id not in todos:
        todos[user_id] = []
    todos[user_id].append(task)
    await update.message.reply_text(f"Задача добавлена: {task}")

async def add_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.chat_id)
    parts = update.message.text.split(maxsplit=2)
    if len(parts) < 3:
        await update.message.reply_text("Формат: /adddate 25.06 День рождения мамы")
        return
    date, note = parts[1], parts[2]
    if user_id not in reminders:
        reminders[user_id] = []
    reminders[user_id].append((date, note))
    await update.message.reply_text(f"Напоминание добавлено: {note} на {date}")

async def test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_personalized_message(update.message.chat_id, context)

async def send_personalized_message(user_id, context):
    user_id = str(user_id)
    data = users.get(user_id)
    if not data:
        return

    today = datetime.datetime.now().strftime("%d.%m")
    text = f"Доброе утро, {data['name']}! 🌞\n"
    for topic in data.get("interests", []):
        if "Гороскоп" in topic:
            text += f"🧙 Гороскоп ({data['zodiac']}): сегодня интуиция поможет принять верные решения.\n"
        if "Криптовалюта" in topic:
            text += "💰 Курс BTC: $65,430, ETH: $3,270.\n"
        if "Игры" in topic:
            text += "🕹 Новинка: обновление для Cyberpunk 2077 доступно!\n"
        if "Красота" in topic:
            text += "💄 Совет: летом важно использовать SPF.\n"
        if "Здоровье" in topic:
            text += "🧘‍♀️ Пей воду и делай разминку — здоровье важнее всего.\n"
        if "Погода" in topic:
            text += f"☀️ Погода в {data['city']}: +23°, ясно.\n"
        if "Факт дня" in topic:
            text += "🧠 Факт: у осьминогов три сердца!\n"
        if "Продуктивность" in topic:
            text += "💼 Совет: используй правило 1-3-5 для планирования задач.\n"
        if "Цитата дня" in topic:
            text += "🧠 Цитата: «Делай или не делай. Нет попыток.» — Йода\n"
        if "Курс валют / крипты" in topic:
            text += "💹 USD: 1.09 | EUR: 1.00 | BTC: $65,000\n"
        if "Совет по питанию" in topic:
            text += "🍽 Завтрак: овсянка с орехами и ягодами — заряд на день.\n"
        if "Рекомендация дня" in topic:
            choice = random.choice(["Книга: 'Атлант расправил плечи'", "Фильм: 'Интерстеллар'", "Игра: 'Hades'"])
            text += f"🎬 Рекомендация: {choice}\n"
        if "Личные напоминания" in topic and user_id in reminders:
            for date, note in reminders[user_id]:
                if date == today:
                    text += f"🎉 Сегодня: {note}!\n"
        if "To-do задачи" in topic and user_id in todos:
            text += "✅ Задачи на день:\n" + "\n".join([f"- {t}" for t in todos[user_id]]) + "\n"

    try:
        await context.bot.send_message(chat_id=int(user_id), text=text)
    except Exception as e:
        print(f"Ошибка при отправке {user_id}: {e}")

async def send_daily_messages(application):
    now = datetime.datetime.now(pytz.timezone("Europe/Brussels")).strftime("%H:%M")
    for user_id, data in users.items():
        if data.get("time") == now:
            await send_personalized_message(user_id, application)

def scheduler(application):
    schedule.every().minute.do(lambda: application.create_task(send_daily_messages(application)))
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    load_users()
    TOKEN = "7855248264:AAEvDeAi-3lC5hbsI3y_H8qYG22aitUzT88"
    app = ApplicationBuilder().token(TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            BIRTHDAY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_birthday)],
            CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_city)],
            TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_time)],
            INTERESTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_interests)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv)
    app.add_handler(CommandHandler("test", test))
    app.add_handler(CommandHandler("addtask", add_task))
    app.add_handler(CommandHandler("adddate", add_date))

    Thread(target=scheduler, args=(app,), daemon=True).start()

    print("Бот запущен...")
    app.run_polling()
