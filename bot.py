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

# ===== Промт для краткого прогноза =====
SPORTS_ANALYST_PROMPT = """
Ты — спортивный ИИ-аналитик, встроенный в Telegram-бота.

Твоя задача — давать чёткий, краткий и структурированный прогноз на матч:
- Укажи команды, дату и время встречи (если известно).
- Выведи итоговый прогноз: кто победит или какой исход наиболее вероятен.
- Предложи 1–2 ставки (П1, ТБ 2.5, ОЗ, Фора и т.д.) и укажи примерные коэффициенты.
- Добавь краткий комментарий аналитика с ключевыми фактами о форме и состоянии команд.
- Пиши в телеграм-стиле, добавляй эмодзи по смыслу (⚽️📊🔥🍀).
- Не давай длинных объяснений, если пользователь об этом не просил.
- Если пользователь попросит пояснение ("почему", "объясни", "поясни" и т.п.), тогда дай подробный разбор: форма команд, ключевые игроки, тактика, статистика.

Всегда начинай с блока прогноза и ставок, как будто это сообщение от профессионального каппера в Telegram.
Формат:
📅 Дата/время:
⚔️ Матч:
📊 Прогноз:
🔥 Краткий комментарий аналитика:
💰 Ставка(и):
"""

# ===== Промт для развёрнутого анализа =====
DETAILED_ANALYST_PROMPT = """
Ты — опытный спортивный аналитик.

Дай короткий, но ёмкий разбор прогноза с ключевыми моментами:
1. Текущая форма и состояние команд/спортсменов.
2. Основные тактические особенности и сильные стороны.
3. Важные статистические данные и личные встречи.
4. Факторы, влияющие на матч (погода, место, мотивация).
5. Итоговый прогноз с обоснованием.
6. Рекомендации по ставкам с коэффициентами.

Пиши кратко, понятно, без лишних деталей, но с достаточным объяснением.
"""

# ===== Функция извлечения информации из текста =====
def extract_match_info(user_text: str):
    """Извлекает команды, дату и время из текста пользователя"""
    today = datetime.now()

    # Дата
    if "сегодня" in user_text.lower():
        match_date = today.strftime("%d.%m.%Y")
    elif "завтра" in user_text.lower():
        match_date = (today + timedelta(days=1)).strftime("%d.%m.%Y")
    elif "послезавтра" in user_text.lower():
        match_date = (today + timedelta(days=2)).strftime("%d.%m.%Y")
    else:
        date_match = re.search(r"\d{1,2}[./-]\d{1,2}([./-]\d{2,4})?", user_text)
        match_date = date_match.group() if date_match else "дата неизвестна"

    # Время (форматы: 19:00, 19.00, 19-00)
    time_match = re.search(r"\b\d{1,2}[:.\-]\d{2}\b", user_text)
    match_time = time_match.group() if time_match else "время неизвестно"

    # Команды
    teams = re.split(r"\s?[-—]\s?| vs | против ", user_text, flags=re.IGNORECASE)
    teams = [t.strip() for t in teams if t.strip()]
    match_teams = " — ".join(teams) if len(teams) >= 2 else "команды не указаны"

    return match_teams, match_date, match_time

# ===== Команда /start =====
@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    await message.answer(
        "Привет! Я твой спортивный аналитик 📊\n"
        "Напиши матч, и я дам краткий прогноз и ставки.\n"
        "Если хочешь подробности — напиши 'почему' или 'объясни'."
    )

# ===== Обработка сообщений =====
@dp.message()
async def handle_message(message: types.Message):
    try:
        # Выбор промта
        if any(word in message.text.lower() for word in ["почему", "объясни", "поясни"]):
            role_prompt = DETAILED_ANALYST_PROMPT
        else:
            role_prompt = SPORTS_ANALYST_PROMPT

        # Извлекаем данные
        match_teams, match_date, match_time = extract_match_info(message.text)

        # Формируем контекст
        user_content = (
            f"Матч: {match_teams}\n"
            f"Дата: {match_date}\n"
            f"Время: {match_time}\n"
            f"Запрос: {message.text}"
        )

        # Запрос к OpenAI
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": role_prompt},
                {"role": "user", "content": user_content}
            ]
        )
        reply = response.choices[0].message.content
        await message.answer(reply)

    except Exception as e:
        logging.error(f"Ошибка: {e}")
        await message.answer("Произошла ошибка при анализе. Попробуй позже.")

# ===== Запуск =====
async def main():
    logging.info("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
