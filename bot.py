import logging
import os
import asyncio
import re
from datetime import datetime, timedelta
import openai
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Настройка OpenAI
openai.api_key = OPENAI_API_KEY

# Инициализация бота
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ===== Промты =====
SPORTS_ANALYST_PROMPT = """
Ты — спортивный ИИ-аналитик, встроенный в Telegram-бота.

Дай структурированный прогноз на матч по следующему шаблону:

🏆 Прогноз на матч: [Команда 1] — [Команда 2]  
📅 Дата: [дата]  
⏰ Время начала: [время]

📊 Вероятность победы (в процентах):  
- [Команда 1]: XX%  
- [Команда 2]: XX%  
- Ничья: XX%

🔥 Краткий комментарий аналитика:  
[Ключевые факты о форме, статистике и состоянии команд]

💡 Возможный исход и рекомендации по ставкам:  
- [Основная ставка с примерным коэффициентом]  
- [Дополнительный вариант для осторожных]

🍀 Удачи! Ставь с умом и не гонись за всем подряд 😉  

Пиши в телеграм-стиле с эмодзи и без лишней воды.
"""


# ===== Хранилище истории сообщений в памяти =====
user_histories = {}
MAX_HISTORY_MESSAGES = 10

def add_message_to_history(user_id: int, role: str, content: str):
    if user_id not in user_histories:
        user_histories[user_id] = []
    user_histories[user_id].append({"role": role, "content": content})
    if len(user_histories[user_id]) > MAX_HISTORY_MESSAGES:
        user_histories[user_id] = user_histories[user_id][-MAX_HISTORY_MESSAGES:]

def extract_match_info(user_text: str):
    today = datetime.now()
    if "сегодня" in user_text.lower():
        match_date = today.strftime("%d.%m.%Y")
    elif "завтра" in user_text.lower():
        match_date = (today + timedelta(days=1)).strftime("%d.%m.%Y")
    elif "послезавтра" in user_text.lower():
        match_date = (today + timedelta(days=2)).strftime("%d.%m.%Y")
    else:
        date_match = re.search(r"\d{1,2}[./-]\d{1,2}([./-]\d{2,4})?", user_text)
        match_date = date_match.group() if date_match else "дата неизвестна"
    time_match = re.search(r"\b\d{1,2}[:.\-]\d{2}\b", user_text)
    match_time = time_match.group() if time_match else "время неизвестно"
    teams = re.split(r"\s?[-—]\s?| vs | против ", user_text, flags=re.IGNORECASE)
    teams = [t.strip() for t in teams if t.strip()]
    match_teams = " — ".join(teams) if len(teams) >= 2 else "команды не указаны"
    return match_teams, match_date, match_time

@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    user_id = message.from_user.id
    user_histories.pop(user_id, None)
    await message.answer(
        "Привет! Я твой спортивный аналитик 📊\n"
        "Напиши матч, и я дам краткий прогноз и ставки.\n"
        "Если хочешь подробности — напиши 'почему' или 'объясни'."
    )

@dp.message()
async def handle_message(message: types.Message):
    user_id = message.from_user.id
    user_text = message.text.strip()
    detailed_requested = any(word in user_text.lower() for word in ["почему", "объясни", "поясни"])
    role_prompt = DETAILED_ANALYST_PROMPT if detailed_requested else SPORTS_ANALYST_PROMPT
    match_teams, match_date, match_time = extract_match_info(user_text)
    user_content = (
        f"Матч: {match_teams}\n"
        f"Дата: {match_date}\n"
        f"Время: {match_time}\n"
        f"Запрос: {user_text}"
    )
    add_message_to_history(user_id, "user", user_content)
    messages = [{"role": "system", "content": role_prompt}] + user_histories[user_id]
    try:
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=messages
        )
        reply = response.choices[0].message.content
        add_message_to_history(user_id, "assistant", reply)
        await message.answer(reply)
    except Exception as e:
        logging.error(f"Ошибка: {e}")
        await message.answer("Произошла ошибка при анализе. Попробуй позже.")

async def main():
    logging.info("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
