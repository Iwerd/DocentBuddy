import logging, json, pytz, datetime, schedule, time, random, requests
from threading import Thread
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ConversationHandler, filters, ContextTypes

NAME, BIRTHDAY, CITY, TIME, INTERESTS = range(5)

TOPICS = [
    "💰 Криптовалюта","🧙 Гороскоп","☀️ Погода",
    "🧠 Цитата дня","💼 Продуктивность","🍽 Совет по питанию",
    "🎬 Рекомендация дня","🎉 Личные напоминания","✅ To‑do задачи"
]

users, reminders, todos = {}, {}, {}
logging.basicConfig(level=logging.INFO)

TOKEN = "7855248264:AAEvDeAi-3lC5hbsI3y_H8qYG22aitUzT88"
OWM_KEY = "bb4019aa070450b7031cee639418b585"
ASTROLOGY_KEY = "U8aD3ZQKnl9qINCHFaa6b4wslb0tyJD15Ii21RBk"

zodiac_map = {
    "Овен": "aries", "Телец": "taurus", "Близнецы": "gemini", "Рак": "cancer",
    "Лев": "leo", "Дева": "virgo", "Весы": "libra", "Скорпион": "scorpio",
    "Стрелец": "sagittarius", "Козерог": "capricorn", "Водолей": "aquarius", "Рыбы": "pisces"
}

def get_crypto():
    try:
        r = requests.get("https://api.coingecko.com/api/v3/simple/price",
                         params={"ids":"bitcoin,ethereum","vs_currencies":"usd","include_24hr_change":"true"})
        d = r.json()
        return (f"💹 *Криптовалюта*:\nBitcoin - ${d['bitcoin']['usd']} ({d['bitcoin']['usd_24h_change']:+.2f}%)\n"
                f"Ethereum - ${d['ethereum']['usd']} ({d['ethereum']['usd_24h_change']:+.2f}%)\n"
                "📊 Вчерашний рост связан с институциональным спросом и снижением давления на рынке.")
    except:
        return "💹 Курс крипты недоступен."

def get_weather(city):
    try:
        r = requests.get("http://api.openweathermap.org/data/2.5/weather",
                         params={"q":city,"units":"metric","appid":OWM_KEY,"lang":"ru"})
        d = r.json()
        desc = d["weather"][0]["description"]
        return (f"☀️ *Погода в {city}*: {d['main']['temp']}°C, {desc}.\n"
                f"Ощущается как {d['main']['feels_like']}°. Уровень влажности: {d['main']['humidity']}%.\n"
                "Совет: возьми зонт, если планируешь прогулку - осадки возможны.")
    except:
        return "☀️ Погода недоступна."

def get_horoscope(sign):
    try:
        eng_sign = zodiac_map.get(sign, "libra")
        r = requests.post(
            "https://api.freeastrologyapi.com/dailyhoroscope",
            headers={
                "x-api-key": ASTROLOGY_KEY,
                "Content-Type": "application/json"
            },
            json={"zodiacName": eng_sign}
        )
        d = r.json()
        return f"🧙 *Гороскоп для {sign}*:\n\n{d['horoscope']}"
    except Exception as e:
        return f"🧙 Гороскоп недоступен. ({e})"

def get_quote():
    q,a = random.choice([
        ("Успех - идти от поражения к поражению без потери энтузиазма.", "У. Черчилль"),
        ("Не откладывай на завтра то, что можно сделать сегодня.", "Б. Франклин")
    ])
    return f"🧠 Цитата дня: «{q}» — {a}.\n\nПопробуй применить это в течение дня и посмотри, как изменится настроение."

def get_productivity():
    return ("💼 *Совет по продуктивности*: Используй метод "
            "Time Blocking - дели день на блоки с конкретными задачами.\n\n"
            "Пример: 9:00-11:00 - работа без отвлечений, 11:30-12:00 - проверка почты и т.д.")

def get_food_advice():
    return ("🍽 *Питание*: Завтрак должен давать заряд энергии.\n\nОвсянка с мёдом и ягодами - отличный старт. Избегай сладких хлопьев и кофе на голодный желудок.")

def get_recommendation():
    return ("🎬 *Рекомендация дня*: Фильм - «Интерстеллар».\n\nФантастика, драма и философия в одном. Вопрос: что важнее - наука или любовь?")

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
    today = datetime.datetime.now().strftime("%d.%m")
    text = f"Доброе утро, {d['name']}!\n\n"
    for t in d["interests"]:
        if "Криптовалюта" in t: text += get_crypto() + "\n\n"
        if "Погода" in t: text += get_weather(d["city"]) + "\n\n"
        if "Гороскоп" in t: text += get_horoscope(d["zodiac"]) + "\n\n"
        if "Цитата дня" in t: text += get_quote() + "\n\n"
        if "Продуктивность" in t: text += get_productivity() + "\n\n"
        if "Совет по питанию" in t: text += get_food_advice() + "\n\n"
        if "Рекомендация дня" in t: text += get_recommendation() + "\n\n"
        if "Личные напоминания" in t:
            for date,n in reminders.get(uid,[]):
                if date == today:
                    text += f"🎉 Сегодня: {n}\n\n"
        if "To‑do задачи" in t and todos.get(uid):
            text += "✅ *Задачи на сегодня:*\n" + "\n".join(f"- {x}" for x in todos[uid]) + "\n\n"
    await context.bot.send_message(chat_id=int(uid), text=text, parse_mode="Markdown")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Как тебя зовут?")
    return NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text
    await update.message.reply_text("Когда у тебя день рождения? (в формате ДД.ММ)")
    return BIRTHDAY

async def get_birthday(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        day, month = map(int, update.message.text.split("."))
        zodiac = get_zodiac(day, month)
        context.user_data["zodiac"] = zodiac
        await update.message.reply_text("В каком ты городе?")
        return CITY
    except:
        await update.message.reply_text("Пожалуйста, введи дату в формате ДД.ММ")
        return BIRTHDAY

async def get_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["city"] = update.message.text
    reply_keyboard = [[t] for t in TOPICS]
    await update.message.reply_text("Выбери интересующие тебя темы:",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True))
    return INTERESTS

async def get_interests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    users[uid] = {
        "name": context.user_data["name"],
        "zodiac": context.user_data["zodiac"],
        "city": context.user_data["city"],
        "interests": [update.message.text]
    }
    save_users()
    await update.message.reply_text("Спасибо! Я буду присылать тебе персональные советы каждый день."
        , reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

async def test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_personalized(update.effective_user.id, context)

if __name__ == "__main__":
    load_users()
    app = ApplicationBuilder().token(TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            BIRTHDAY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_birthday)],
            CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_city)],
            INTERESTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_interests)],
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