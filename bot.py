import logging, json, schedule, time, asyncio, openai
from threading import Thread
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, filters, ContextTypes

# Состояния диалога
(THEME_SELECTION, NAME, BIRTHDAY, CITY) = range(4)

TOKEN = "7855248264:AAEvDeAi-3lC5hbsI3y_H8qYG22aitUzT88"
OPENAI_API_KEY = "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"

openai.api_key = OPENAI_API_KEY
users = {}
logging.basicConfig(level=logging.INFO)

TOPICS = [
    "💰 Криптовалюта","🧙 Гороскоп","☀️ Погода",
    "💼 Продуктивность","🍽 Совет по питанию","🎬 Рекомендация дня"
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

# OpenAI генератор контента
def generate_content(prompt):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=400,
        temperature=0.8
    )
    return response['choices'][0]['message']['content']

# Отправка персонализированного сообщения
async def send_personalized(uid, context):
    uid = str(uid)
    d = users.get(uid)
    if not d: return
    message = f"Доброе утро, {d['name']}!\n\n"
    for topic in d['interests']:
        prompt = f"Создай интересный и уникальный текст (примерно 100-150 слов) на тему '{topic}' специально для человека по имени {d['name']}."
        if topic == "🧙 Гороскоп":
            prompt += f" Его знак зодиака {d['zodiac']}."
        if topic == "☀️ Погода":
            prompt += f" Он живёт в городе {d['city']}."
        content = generate_content(prompt)
        message += f"{topic}\n{content}\n\n"
    await context.bot.send_message(chat_id=int(uid), text=message)

# Начало общения
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['interests'] = []
    keyboard = [[InlineKeyboardButton(t, callback_data=t)] for t in TOPICS]
    keyboard.append([InlineKeyboardButton("✅ Готово", callback_data="done")])
    await update.message.reply_text("Выбери темы:", reply_markup=InlineKeyboardMarkup(keyboard))
    return THEME_SELECTION

async def theme_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    choice = query.data
    if choice == "done":
        if not context.user_data["interests"]:
            await query.edit_message_text("Выбери хотя бы одну тему.", reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton(t, callback_data=t)] for t in TOPICS] + [[InlineKeyboardButton("✅ Готово", callback_data="done")]]))
            return THEME_SELECTION
        await query.edit_message_reply_markup(None)
        await query.message.reply_text("Как тебя зовут?")
        return NAME
    if choice in context.user_data["interests"]:
        context.user_data["interests"].remove(choice)
    else:
        context.user_data["interests"].append(choice)
    await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(
        [[InlineKeyboardButton(t + (" ✅" if t in context.user_data['interests'] else ""), callback_data=t)] for t in TOPICS] + [[InlineKeyboardButton("✅ Готово", callback_data="done")]]))
    return THEME_SELECTION

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text
    await update.message.reply_text("Когда у тебя день рождения? (ДД.ММ)")
    return BIRTHDAY

async def get_birthday(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["zodiac"] = update.message.text
    await update.message.reply_text("В каком ты городе?")
    return CITY

async def get_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    context.user_data["city"] = update.message.text
    users[uid] = context.user_data
    save_users()
    await update.message.reply_text("Спасибо! Теперь каждое утро я пришлю персональный контент.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

async def test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_personalized(update.effective_user.id, context)

# Запуск приложения
if __name__ == "__main__":
    load_users()
    app = ApplicationBuilder().token(TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            THEME_SELECTION: [CallbackQueryHandler(theme_selection)],
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            BIRTHDAY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_birthday)],
            CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_city)]
        },
        fallbacks=[]
    )

    app.add_handler(conv)
    app.add_handler(CommandHandler("test", test))

    # Планировщик отправки
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
