import logging, json, schedule, time, random, requests, asyncio
from threading import Thread
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
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

def get_crypto():
    return "💹 *Криптовалюта*: BTC $67000, ETH $3500\n📊 Данные обновляются ежедневно."

def get_weather(city):
    return f"☀️ *Погода в {city}*: 20°C, солнечно.\nВозьми зонт только если ты очень осторожный человек!"

def get_generated_horoscope(sign):
    blocks = {
        "work": [
            "Сосредоточься на приоритетных задачах — день обещает быть продуктивным.",
            "Не торопись принимать решения на работе — сначала всё взвесь.",
            "Прояви инициативу — это может принести неожиданный успех."
        ],
        "health": [
            "Организм требует отдыха. Не пренебрегай полноценным сном.",
            "Лёгкая физическая активность улучшит настроение и тонус.",
            "Питайся сбалансированно, особенно избегай лишнего сахара."
        ],
        "emotion": [
            "День подойдёт для общения с близкими и укрепления связей.",
            "Старайся избегать конфликтов — спокойствие принесёт победу.",
            "Прислушайся к интуиции — она сегодня особенно точна."
        ],
        "advice": [
            "Совет: не забывай про личные цели — даже в суете дня.",
            "Совет: удели время себе — прогулка или книга зарядят энергией.",
            "Совет: новые идеи сегодня особенно перспективны — запиши их."
        ]
    }
    text = f"🧙 *Гороскоп для {sign}*:\n\n"
    text += random.choice(blocks["work"]) + "\n"
    text += random.choice(blocks["health"]) + "\n"
    text += random.choice(blocks["emotion"]) + "\n\n"
    text += random.choice(blocks["advice"])
    return text

def get_quote():
    q, a = random.choice([
        ("Успех - идти от поражения к поражению без потери энтузиазма.", "У. Черчилль"),
        ("Не откладывай на завтра то, что можно сделать сегодня.", "Б. Франклин")
    ])
    return f"🧠 Цитата дня: «{q}» — {a}.\n\nПопробуй применить это в течение дня!"

def get_productivity():
    return ("💼 *Совет по продуктивности*: Используй метод Time Blocking — дели день на блоки с конкретными задачами.\n"
            "Пример: 9:00-11:00 — работа без отвлечений, 11:30-12:00 — проверка почты.")

def get_food_advice():
    return "🍽 *Питание*: Начни утро с овсянки и фруктов. Избегай сладких хлопьев и кофе на голодный желудок."

def get_recommendation():
    return "🎬 *Рекомендация дня*: Фильм — «Интерстеллар». Задумайся: что важнее — наука или любовь?"

def get_zodiac(day, month):
    zodiac = [(20,"Козерог"),(19,"Водолей"),(20,"Рыбы"),(20,"Овен"),(21,"Телец"),(21,"Близнецы"),
              (23,"Рак"),(23,"Лев"),(23,"Дева"),(23,"Весы"),(23,"Скорпион"),(22,"Стрелец"),(31,"Козерог")]
    return zodiac[month-1][1] if day < zodiac[month-1][0] else zodiac[month][1]

def load_users():
    global users
    try:
        with open("users.json","r") as f: users = json.load(f)
    except: users = {}

def save_users():
    with open("users.json","w") as f: json.dump(users, f, indent=2)

async def send_personalized(uid, context):
    uid = str(uid)
    d = users.get(uid)
    if not d: return
    text = f"Доброе утро, {d.get('name','друг')}!\n\n"
    for t in d.get("interests", []):
        if "Криптовалюта" in t: text += get_crypto() + "\n\n"
        if "Погода" in t and d.get("city"): text += get_weather(d.get("city")) + "\n\n"
        if "Гороскоп" in t and d.get("zodiac"): text += get_generated_horoscope(d.get("zodiac")) + "\n\n"
        if "Цитата дня" in t: text += get_quote() + "\n\n"
        if "Продуктивность" in t: text += get_productivity() + "\n\n"
        if "Совет по питанию" in t: text += get_food_advice() + "\n\n"
        if "Рекомендация дня" in t: text += get_recommendation() + "\n\n"
    await context.bot.send_message(chat_id=int(uid), text=text, parse_mode="Markdown")

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
        await asyncio.sleep(0.5)
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

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text if update.message.text != "Пропустить" else ""
    await update.message.reply_text("Когда у тебя день рождения? (ДД.ММ)", reply_markup=skip_markup())
    return BIRTHDAY

async def get_birthday(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text != "Пропустить":
        try:
            day, month = map(int, text.split("."))
            context.user_data["zodiac"] = get_zodiac(day, month)
        except:
            await update.message.reply_text("Формат даты неверный. Пример: 24.09")
            return BIRTHDAY
    else:
        context.user_data["zodiac"] = ""
    await update.message.reply_text("В каком ты городе?", reply_markup=skip_markup())
    return CITY

async def get_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["city"] = update.message.text if update.message.text != "Пропустить" else ""
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
