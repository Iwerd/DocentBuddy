# DocentBuddy Telegram Bot

A daily personalized newsletter bot built with `python-telegram-bot`.

## Features
- Interactive setup (`/start`) asking name, birthday, city, time and interests
- Daily message with cryptocurrency rates, weather, horoscope and more
- Add tasks and reminder dates using `/addtask` and `/adddate`
- Test message at any time with `/test`

User data is stored in `users.json`, while tasks and reminders are kept in memory.

## Running
Install requirements and run `bot.py`:
```bash
pip install -r requirements.txt
python bot.py
```
