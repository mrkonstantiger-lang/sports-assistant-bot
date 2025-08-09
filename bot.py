import logging
import os
import asyncio
import re
import sqlite3
from datetime import datetime, timedelta
from dotenv import load_dotenv
import httpx
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from openai import OpenAI

# Загружаем переменные окружения
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
THE_SPORTS_DB_API_KEY = os.getenv("THE_SPORTS_DB_API_KEY")

# Логирование
logging.basicConfig(level=logging.INFO)

# Инициализация OpenAI клиента
client = OpenAI(api_key=OPENAI_API_KEY)

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Создание БД
def init_db():
    conn = sqlite3.connect("chat_history.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            role TEXT,
            content TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def save_message(user_id: int, role: str, content: str):
    conn = sqlite3.connect("chat_history.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO messages (user_id, role, content) VALUES (?, ?, ?)",
        (user_id, role, content)
    )
    conn.commit()
    conn.close()

def get_user_history(user_id, limit=20):
    conn = sqlite3.connect("chat_history.db")
    cursor = conn.cursor()
    cursor.execute('''
        SELECT role, content FROM messages
        WHERE user_id = ?
        ORDER BY timestamp DESC
        LIMIT ?
    ''', (user_id, limit))
    rows = cursor.fetchall()
    conn.close()
    return [{"role": role, "content": content} for role, content in reversed(rows)]

SPORTS_ANALYST_PROMPT = """
Ты — спортивный ИИ-аналитик, встроенный в Telegram-бота.

Всегда пиши ответ строго по этому шаблону и не отклоняйся от него.  
Не добавляй текст вне этих блоков и не меняй их порядок.  

Формат:
📅 Дата: [дата матча]  
⚔️ Матч: [команда 1] — [команда 2]  
📊 Прогноз: [краткий прогноз, кто победит или вероятный исход]  

💰 Ставка 1: [ставка] с коэффициентом ~[коэф]  
💰 Ставка 2: [ставка] с коэффициентом ~[коэф]  

🔥 Краткий комментарий аналитика: [1–2 предложения о форме команд, ключевых факторах, без лишней воды]  

🍀 Пожелание: [краткое мотивирующее пожелание в спортивном стиле, например "Удачи! Ставь с умом! ⚽️🔥"]

Правила:
- Обязательно заполняй все поля.
- Даты и команды должны совпадать с запросом пользователя.
- Пиши в телеграм-стиле с эмодзи.
- Никаких длинных пояснений, только краткий комментарий.
- Пожелание всегда в конце.
"""

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

# Получение следующего матча команды из TheSportsDB
async def get_next_match(team_name: str):
    if not THE_SPORTS_DB_API_KEY:
        return None
    async with httpx.AsyncClient() as client:
        url_team = f"https://www.thesportsdb.com/api/v1/json/{THE_SPORTS_DB_API_KEY}/searchteams.php?t={team_name}"
        res_team = await client.get(url_team)
        if res_team.status_code != 200:
            return None
        data_team = res_team.json()
        if not data_team or not data_team.get("teams"):
            return None
        team_id = data_team["teams"][0]["idTeam"]

        url_events = f"https://www.thesportsdb.com/api/v1/json/{THE_SPORTS_DB_API_KEY}/eventsnext.php?id={team_id}"
        res_events = await client.get(url_events)
        if res_events.status_code != 200:
            return None
        data_events = res_events.json()
        events = data_events.get("events", [])
        if not events:
            return None
        next_event = events[0]
        return {
            "date": next_event.get("dateEvent", "неизвестна"),
            "time": next_event.get("strTime", "время неизвестно"),
            "home_team": next_event.get("strHomeTeam", ""),
            "away_team": next_event.get("strAwayTeam", ""),
            "league": next_event.get("strLeague", "")
        }

# Обёртка синхронного метода openai в async
async def get_openai_response(messages):
    try:
        response = await asyncio.to_thread(
            client.chat.completions.create,
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=800,
            temperature=0.7,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logging.error(f"OpenAI error: {e}")
        return "Ошибка при обработке запроса к OpenAI."

@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    await message.answer(
        "Привет! Я твой спортивный аналитик 📊\n"
        "Напиши матч, и я дам краткий прогноз и ставки.\n"
        "Если хочешь подробности — напиши 'почему' или 'объясни'."
    )

@dp.message()
async def handle_message(message: types.Message):
    user_id = message.from_user.id
    user_text = message.text

    await message.answer("Получил твой запрос! Работаю над прогнозом...")

    try:
        save_message(user_id, "user", user_text)

        if any(word in user_text.lower() for word in ["почему", "объясни", "поясни"]):
            role_prompt = DETAILED_ANALYST_PROMPT
        else:
            role_prompt = SPORTS_ANALYST_PROMPT

        match_teams, match_date, match_time = extract_match_info(user_text)
        team_name = match_teams.split(" — ")[0] if " — " in match_teams else None

        external_info = ""
        if team_name:
            next_match = await get_next_match(team_name)
            if next_match:
                external_info = (
                    f"\n\nИнформация из TheSportsDB:\n"
                    f"Следующий матч команды {team_name}:\n"
                    f"{next_match['home_team']} — {next_match['away_team']} "
                    f"в лиге {next_match['league']} на дату {next_match['date']} "
                    f"время {next_match['time']}."
                )

        history = get_user_history(user_id)
        history.append({"role": "user", "content": user_text + external_info})

        messages = [{"role": "system", "content": role_prompt}] + history

        response_text = await get_openai_response(messages)

        save_message(user_id, "assistant", response_text)

        await message.answer(response_text)

    except Exception as e:
        logging.error(f"Ошибка обработки сообщения: {e}")
        await message.answer("Произошла ошибка при обработке запроса.")

if __name__ == "__main__":
    asyncio.run(dp.start_polling(bot))
