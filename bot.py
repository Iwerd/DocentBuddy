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

OWM_KEY = "bb4019aa070450b7031cee639418b585"
ASTROLOGY_KEY = "U8aD3ZQKnl9qINCHFaa6b4wslb0tyJD15Ii21RBk"

# Данные
zodiac_map = {
    "Овен": "aries", "Телец": "taurus", "Близнецы": "gemini", "Рак": "cancer",
    "Лев": "leo", "Дева": "virgo", "Весы": "libra", "Скорпион": "scorpio",
    "Стрелец": "sagittarius", "Козерог": "capricorn", "Водолей": "aquarius", "Рыбы": "pisces"
}

# API

def get_crypto():
    try:
        r = requests.get("https://api.coingecko.com/api/v3/simple/price",
                         params={"ids":"bitcoin,ethereum","vs_currencies":"usd","include_24hr_change":"true"})
        d = r.json()
        return (f"💹 *Криптовалюта*:\nBitcoin - ${d['bitcoin']['usd']} ({d['bitcoin']['usd_24h_change']:+.2f}%)\n"
                f"Ethereum - ${d['ethereum']['usd']} ({d['ethereum']['usd_24h_change']:+.2f}%)\n"
                "📊 Вчерашний рост связан с институциональным спросом и снижением давления на рынке."
        )
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
            "Пример: 9:00-11:00 - работа без отвлечений, 11:30-12:00 - проверка почты и т.д."
    )

def get_food_advice():
    return ("🍽 *Питание*: Завтрак должен давать заряд энергии.\n\nОвсянка с мёдом и ягодами - отличный старт. Избегай сладких хлопьев и кофе на голодный желудок."
    )

def get_recommendation():
    return ("🎬 *Рекомендация дня*: Фильм - «Интерстеллар».\n\nФантастика, драма и философия в одном. Вопрос: что важнее - наука или любовь?"
    )

# Служебные

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

# Блок отправки

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
