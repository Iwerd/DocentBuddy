import logging, json, pytz, datetime, schedule, time, random, requests
from threading import Thread
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ConversationHandler, filters, ContextTypes

# Стадии
NAME, BIRTHDAY, CITY, TIME, INTERESTS = range(5)

TOPICS = [
    "💰 Криптовалюта","🧙 Гороскоп","☀️ Погода",
    "🧠 Цитата дня","💼 Продуктивность","🍽 Совет по питанию",
    "🎬 Рекомендация дня","🎉 Личные напоминания","✅ To‑do задачи"
]

users, reminders, todos = {}, {}, {}
logging.basicConfig(level=logging.INFO)

def load_users():
    global users
    try:
        with open("users.json","r") as f: users = json.load(f)
    except: users = {}
def save_users():
    with open("users.json","w") as f: json.dump(users, f, indent=2)

def get_zodiac(day, month):
    zodiac = [(20,"Козерог"),(19,"Водолей"),(20,"Рыбы"),(20,"Овен"),
              (21,"Телец"),(21,"Близнецы"),(23,"Рак"),(23,"Лев"),
              (23,"Дева"),(23,"Весы"),(23,"Скорпион"),(22,"Стрелец"),(31,"Козерог")]
    return zodiac[month-1][1] if day < zodiac[month-1][0] else zodiac[month][1]

# --- API ---
def get_crypto():
    try:
        r = requests.get("https://api.coingecko.com/api/v3/simple/price",
                         params={"ids":"bitcoin,ethereum","vs_currencies":"usd","include_24hr_change":"true"})
        d = r.json()
        return (f"💹 *Криптовалюта*: BTC — ${d['bitcoin']['usd']} "
                f"({d['bitcoin']['usd_24h_change']:+.2f}%), "
                f"ETH — ${d['ethereum']['usd']} "
                f"({d['ethereum']['usd_24h_change']:+.2f}%)")
    except:
        return "💹 Курс крипты недоступен."

OWM_KEY = "bb4019aa070450b7031cee639418b585"
def get_weather(city):
    try:
        r = requests.get("http://api.openweathermap.org/data/2.5/weather",
                         params={"q":city,"units":"metric","appid":OWM_KEY,"lang":"ru"})
        d = r.json()
        desc = d["weather"][0]["description"]
        return (f"☀️ *Погода в {city}*: {d['main']['temp']}°C, {desc}. "
                f"Ощущается как {d['main']['feels_like']}°.")
    except:
        return "☀️ Погода недоступна."

NINJA_KEY = "FfcKhX0kzpk8H4I4ky5eJA==LJa8iY0IYvY0hZ79"
def get_horoscope(sign):
    try:
        r = requests.get("https://api.api-ninjas.com/v1/horoscope",
                         params={"zodiac":sign.lower()},
                         headers={"X-Api-Key": NINJA_KEY})
        txt = r.json().get("horoscope","")
        return f"🧙 *Гороскоп для {sign}*: {txt}"
    except:
        return f"🧙 Гороскоп для {sign} недоступен."

def get_quote():
    q,a = random.choice([
        ("Успех — идти от поражений к победам без потери энтузиазма.", "У. Черчилль"),
        ("Не откладывай на завтра то, что можно сделать сегодня.", "Б. Франклин")
    ])
    return f"🧠 Цитата дня: «{q}» — {a}."

def get_productivity():
    tips = [
        "Применяй технику Pomodoro: 25 мин работы и 5 мин отдыха.",
        "Планируй задачи по правилу 1‑3‑5: 1 важная, 3 средней важности, 5 мелких."
    ]
    return f"💼 *Совет по продуктивности*: {random.choice(tips)}"

def get_food_advice():
    return ("🍽 *Совет по питанию*: начни день с овсянки с ягодами — это "
            "долгосрочная энергия и отличное пищеварение.")

def get_recommendation():
    recs = [
        "📚 Книга: «Атлант расправил плечи» — философский эпик о силе человека.",
        "🎞 Фильм: «Интерстеллар» — космическая драма, философия и эмоции.",
        "🎮 Игра: Hades — динамичный рогалик с глубоким сюжетом."
    ]
    return f"🎬 *Рекомендация дня*: {random.choice(recs)}"

# --- Рассылка ---
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

# --- Команды и диалог ---
async def start(update, context):
    await update.message.reply_text("Привет! Как тебя зовут?")
    return NAME
async def get_name(update, context):
    context.user_data["name"] = update.message.text
    await update.message.reply_text("Когда твой день рождения? (ДД.ММ.ГГГГ)")
    return BIRTHDAY
async def get_birthday(update, context):
    try:
        b = datetime.datetime.strptime(update.message.text, "%d.%m.%Y")
        context.user_data["birthday"] = update.message.text
        context.user_data["zodiac"] = get_zodiac(b.day, b.month)
        await update.message.reply_text("В каком городе ты живёшь?")
        return CITY
    except:
        await update.message.reply_text("Формат: ДД.MM.ГГГГ")
        return BIRTHDAY
async def get_city(update, context):
    context.user_data["city"] = update.message.text
    await update.message.reply_text("Во сколько тебе удобно получать рассылку? (например, 08:00)")
    return TIME
async def get_time(update, context):
    context.user_data["time"] = update.message.text
    return await ask_interests(update, context)
async def ask_interests(update, context):
    keyboard = [[t] for t in TOPICS] + [["✅ Готово"]]
    reply = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
    context.user_data["interests"] = []
    await update.message.reply_text("Выбери темы для рассылки:", reply_markup=reply)
    return INTERESTS
async def collect_interests(update, context):
    c = update.message.text
    if c == "✅ Готово":
        users[str(update.message.chat_id)] = context.user_data
        save_users()
        await update.message.reply_text("Настройки сохранены!", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    if c in TOPICS:
        context.user_data["interests"].append(c)
        await update.message.reply_text(f"Добавлено: {c}")
    return INTERESTS
async def add_task(update, context):
    uid = str(update.message.chat_id)
    task = " ".join(context.args)
    todos.setdefault(uid, []).append(task)
    await update.message.reply_text(f"Задача добавлена: {task}")
async def add_date(update, context):
    uid = str(update.message.chat_id)
    parts = update.message.text.split(maxsplit=2)
    if len(parts)<3:
        await update.message.reply_text("Формат: /adddate 25.06 Описание")
        return
    date, note = parts[1], parts[2]
    reminders.setdefault(uid, []).append((date, note))
    await update.message.reply_text(f"Напоминание: \"{note}\" на {date} добавлено.")
async def test(update, context):
    await send_personalized(update.message.chat_id, context)

async def send_daily(app):
    now = datetime.datetime.now(pytz.timezone("Europe/Brussels")).strftime("%H:%M")
    for uid,d in users.items():
        if d.get("time")==now:
            await send_personalized(uid, app)

def scheduler(app):
    schedule.every().minute.do(lambda: app.create_task(send_daily(app)))
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__=="__main__":
    load_users()
    TOKEN = "7855248264:AAEvDeAi-3lC5hbsI3y_H8qYG22aitUzT88"
    app = ApplicationBuilder().token(TOKEN).build()
    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            NAME:[MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            BIRTHDAY:[MessageHandler(filters.TEXT & ~filters.COMMAND, get_birthday)],
            CITY:[MessageHandler(filters.TEXT & ~filters.COMMAND, get_city)],
            TIME:[MessageHandler(filters.TEXT & ~filters.COMMAND, get_time)],
            INTERESTS:[MessageHandler(filters.TEXT & ~filters.COMMAND, collect_interests)],
        },
        fallbacks=[CommandHandler("cancel", lambda u,c: ConversationHandler.END)]
    )
    app.add_handler(conv)
    app.add_handler(CommandHandler("test", test))
    app.add_handler(CommandHandler("addtask", add_task))
    app.add_handler(CommandHandler("adddate", add_date))
    Thread(target=scheduler, args=(app,), daemon=True).start()
    print("Бот запущен...")
    app.run_polling()
