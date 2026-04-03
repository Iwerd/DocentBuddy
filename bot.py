import logging
import json
import schedule
import time
import asyncio
import openai
from threading import Thread
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)

# Состояния диалога
(
    THEME_SELECTION,
    NAME,
    BIRTHDAY,
    CITY,
    PROFESSION,
    SLEEP,
    GOALS,
    HOBBIES,
    MORNING_PRODUCTIVITY,
    NOTIFY_TIME,
) = range(10)

TOKEN = "TOKEN HERE"
OPENAI_API_KEY = "API HERE"

openai.api_key = OPENAI_API_KEY
users = {}
logging.basicConfig(level=logging.INFO)

TOPICS = [
    "💰 Криптовалюта",
    "🧙 Гороскоп",
    "☀️ Погода",
    "🧠 Цитата дня",
    "💼 Продуктивность",
    "🍽 Совет по питанию",
    "🎬 Рекомендация дня",
    "🎉 Личные напоминания",
    "✅ To‑do задачи",
]


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


def skip_markup():
    return ReplyKeyboardMarkup([["Пропустить"]], resize_keyboard=True, one_time_keyboard=True)


# =========================== OpenAI генерация ===============================
def generate_content(prompt, max_tokens=380):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        temperature=0.9,
    )
    return response["choices"][0]["message"]["content"]


# =========================== Рассылка ===============================
async def send_personalized(uid, context):
    uid = str(uid)
    d = users.get(uid)
    if not d:
        return
    message = f"Доброе утро, {d.get('name','друг')}!\n\n"
    for topic in d["interests"]:
        prompt = f"Сгенерируй уникальный, подробный текст на русском языке (минимум 120 слов, можно с советом, юмором, или интересным фактом) по теме «{topic}» для пользователя с такими данными: "
        if d.get("name"):
            prompt += f"Имя: {d['name']}. "
        if topic == "🧙 Гороскоп" and d.get("zodiac"):
            prompt += f"Знак зодиака: {d['zodiac']}. "
        if topic == "☀️ Погода" and d.get("city"):
            prompt += f"Город: {d['city']}. "
        if d.get("profession"):
            prompt += f"Профессия: {d['profession']}. "
        if d.get("sleep"):
            prompt += f"Сон: {d['sleep']} часов. "
        if d.get("goals"):
            prompt += f"Цели месяца: {d['goals']}. "
        if d.get("hobbies"):
            prompt += f"Хобби: {d['hobbies']}. "
        if d.get("morning"):
            prompt += f"Продуктивность утром: {d['morning']}. "
        prompt += "Ответ должен быть информативным и персональным."
        content = generate_content(prompt)
        message += f"{topic}\n{content}\n\n"
    await context.bot.send_message(chat_id=int(uid), text=message)


# =========================== Диалог регистрации ===============================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["interests"] = []
    await update.message.reply_text(
        "Привет! Выбери интересующие тебя темы:",
        reply_markup=generate_topic_markup([]),
    )
    return THEME_SELECTION


def generate_topic_markup(selected):
    keyboard = [
        [InlineKeyboardButton(t + (" ✅" if t in selected else ""), callback_data=t)] for t in TOPICS
    ]
    keyboard.append([InlineKeyboardButton("✅ Готово", callback_data="done")])
    return InlineKeyboardMarkup(keyboard)


async def theme_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    choice = query.data

    if choice == "done":
        if not context.user_data["interests"]:
            await query.edit_message_text(
                "Выбери хотя бы одну тему.",
                reply_markup=generate_topic_markup([]),
            )
            return THEME_SELECTION
        await query.edit_message_reply_markup(reply_markup=None)
        await asyncio.sleep(0.3)
        await query.message.reply_text("Как тебя зовут?", reply_markup=skip_markup())
        return NAME

    if choice in context.user_data["interests"]:
        context.user_data["interests"].remove(choice)
    else:
        context.user_data["interests"].append(choice)

    await query.edit_message_reply_markup(
        reply_markup=generate_topic_markup(context.user_data["interests"])
    )
    return THEME_SELECTION


async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = (
        update.message.text if update.message.text != "Пропустить" else ""
    )
    await update.message.reply_text("Когда у тебя день рождения? (ДД.ММ)", reply_markup=skip_markup())
    return BIRTHDAY


async def get_birthday(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text != "Пропустить":
        try:
            day, month = map(int, text.split("."))
            context.user_data["zodiac"] = get_zodiac(day, month)
        except:
            context.user_data["zodiac"] = ""
    else:
        context.user_data["zodiac"] = ""
    await update.message.reply_text("В каком ты городе?", reply_markup=skip_markup())
    return CITY


def get_zodiac(day, month):
    zodiac = [
        (20, "Козерог"),
        (19, "Водолей"),
        (20, "Рыбы"),
        (20, "Овен"),
        (21, "Телец"),
        (21, "Близнецы"),
        (23, "Рак"),
        (23, "Лев"),
        (23, "Дева"),
        (23, "Весы"),
        (23, "Скорпион"),
        (22, "Стрелец"),
        (31, "Козерог"),
    ]
    return zodiac[month - 1][1] if day < zodiac[month - 1][0] else zodiac[month][1]


async def get_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["city"] = (
        update.message.text if update.message.text != "Пропустить" else ""
    )
    await update.message.reply_text("Чем ты занимаешься? (профессия/деятельность)", reply_markup=skip_markup())
    return PROFESSION


async def get_profession(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["profession"] = (
        update.message.text if update.message.text != "Пропустить" else ""
    )
    await update.message.reply_text("Сколько ты обычно спишь в сутки (в часах)?", reply_markup=skip_markup())
    return SLEEP


async def get_sleep(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["sleep"] = (
        update.message.text if update.message.text != "Пропустить" else ""
    )
    await update.message.reply_text("Какие цели ставишь перед собой на этот месяц?", reply_markup=skip_markup())
    return GOALS


async def get_goals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["goals"] = (
        update.message.text if update.message.text != "Пропустить" else ""
    )
    await update.message.reply_text("Чем ты любишь заниматься в свободное время?", reply_markup=skip_markup())
    return HOBBIES


async def get_hobbies(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["hobbies"] = (
        update.message.text if update.message.text != "Пропустить" else ""
    )
    await update.message.reply_text(
        "Как ты оцениваешь свою продуктивность утром? (низкая / средняя / высокая)",
        reply_markup=skip_markup(),
    )
    return MORNING_PRODUCTIVITY


async def get_productivity_level(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["morning"] = (
        update.message.text if update.message.text != "Пропустить" else ""
    )
    await update.message.reply_text(
        "Во сколько тебе удобно получать утренние сообщения? (например, 08:00)",
        reply_markup=skip_markup(),
    )
    return NOTIFY_TIME


async def get_notify_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["notify"] = (
        update.message.text if update.message.text != "Пропустить" else "08:00"
    )
    uid = str(update.effective_user.id)
    users[uid] = dict(context.user_data)
    save_users()
    await update.message.reply_text(
        "Спасибо! Я буду присылать тебе персональные советы каждый день.",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END


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
        fallbacks=[],
    )

    app.add_handler(conv)
    app.add_handler(CommandHandler("test", test))

    def run_scheduler():
        while True:
            schedule.run_pending()
            time.sleep(10)

    def schedule_job():
        for uid in users:
            asyncio.run(send_personalized(uid, app))

    schedule.every().day.at("08:00").do(schedule_job)
    Thread(target=run_scheduler, daemon=True).start()

    print("🤖 Бот запущен и готов к работе!")
    app.run_polling()
