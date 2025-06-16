import logging
import json
import pytz
import datetime
import schedule
import time
from threading import Thread
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ConversationHandler, filters, ContextTypes
)

# Стадии диалога
NAME, BIRTHDAY, CITY, TIME, INTERESTS = range(5)

# Интересы пользователя
TOPICS = [
    "💰 Криптовалюта",
    "🤙 Гороскоп",
    "🔹 Игры",
    "💅 Красота",
    "🧘‍♀️ Здоровье",
    "☀️ Погода",
    "🧐 Факт дня"
]

# Загрузка и сохранение пользователей

def load_users():
    try:
        with open("users.json", "r") as f:
            return json.load(f)
    except:
        return {}

def save_users(users):
    with open("users.json", "w") as f:
        json.dump(users, f, indent=2)

users = load_users()

# Логгирование
logging.basicConfig(level=logging.INFO)

# Определение знака зодиака

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

# Диалоговые этапы

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
    await update.message.reply_text(
        "Выбери, что тебе интересно (можно несколько). Когда закончишь — нажми «Готово».",
        reply_markup=reply_markup
    )
    return INTERESTS

async def collect_interests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    choice = update.message.text
    if choice == "✅ Готово":
        user_id = str(update.message.chat_id)
        users[user_id] = context.user_data
        save_users(users)
        await update.message.reply_text(
            f"Спасибо! С завтрашнего дня я буду присылать тебе полезную информацию по темам: {', '.join(context.user_data['interests'])}.",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END
    elif choice in TOPICS:
        if choice not in context.user_data["interests"]:
            context.user_data["interests"].append(choice)
        await update.message.reply_text(f"Добавлено: {choice}")
    return INTERESTS

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Окей, если что — напиши /start.")
    return ConversationHandler.END

# Ежедневная отправка сообщений

async def send_daily_messages(application):
    now = datetime.datetime.now(pytz.timezone("Europe/Brussels")).strftime("%H:%M")
    for user_id, data in users.items():
        if data.get("time") == now:
            text = f"Доброе утро, {data['name']}! \ud83c\udf1e\n"
            for topic in data.get("interests", []):
                if "Гороскоп" in topic:
                    text += f"🤙 Гороскоп для {data['zodiac']}: сегодня стоит доверять интуиции.\n"
                if "Криптовалюта" in topic:
                    text += "💰 Биткойн поднялся на 2%, но сохраняй внимательность.\n"
                if "Игры" in topic:
                    text += "🔹 Вышел патч для Cyberpunk 2077.\n"
                if "Красота" in topic:
                    text += "💅 Увлажняющие сысыворотки особенно актуальны летом.\n"
                if "Здоровье" in topic:
                    text += "🧘‍♀️ Не забудь сделать разминку и выпить воды 💧\n"
                if "Погода" in topic:
                    text += f"☀️ В {data['city']} ожидается тепло и солнце.\n"
                if "Факт дня" in topic:
                    text += "🧐 Факт: у осьминогов 3 сердца!\n"
            try:
                await application.bot.send_message(chat_id=int(user_id), text=text)
            except Exception as e:
                print(f"Ошибка при отправке пользователю {user_id}: {e}")

# Планировщик

def scheduler(application):
    schedule.every().minute.do(lambda: application.create_task(send_daily_messages(application)))
    while True:
        schedule.run_pending()
        time.sleep(1)

# Запуск
if __name__ == "__main__":
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

    Thread(target=scheduler, args=(app,), daemon=True).start()

    print("Бот запущен...")
    app.run_polling()
