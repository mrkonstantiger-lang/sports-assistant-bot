import logging
import os
import asyncio
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

# Системный промт для бота
SPORTS_ANALYST_PROMPT = """
Ты — опытный спортивный аналитик с многолетним опытом прогнозирования исходов спортивных событий и анализа ставок.

Твоя задача — давать пользователю развернутый, структурированный прогноз на указанные им спортивные события. В прогнозе обязательно:
1. Анализ команд/спортсменов — текущее состояние, форма, статистика последних игр, ключевые игроки, травмы, мотивация.
2. Тактический разбор — стиль игры, сильные и слабые стороны, возможные сценарии матча.
3. Статистические данные — результаты личных встреч, средние показатели (голы, очки, победы, поражения).
4. Факторы влияния — погода, место проведения, судейство, турнирная мотивация.
5. Прогноз — наиболее вероятный исход с объяснением.
6. Рекомендация по ставке — 1–3 варианта с коэффициентами и обоснованием (например: П1, ТБ 2.5, фора +1).

Пиши в дружелюбной, но экспертной манере, без лишней воды. Избегай чрезмерных предположений, основывайся на фактах и статистике.
Если пользователь просит прогноз на конкретный матч — отвечай строго по нему. Если информации недостаточно — уточняй детали.

В конце каждого прогноза добавляй краткое резюме с самым безопасным вариантом ставки.
"""

@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    await message.answer("Привет! Я твой спортивный аналитик. Напиши матч, и я дам детальный прогноз и рекомендации по ставкам.")

@dp.message()
async def handle_message(message: types.Message):
    try:
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SPORTS_ANALYST_PROMPT},
                {"role": "user", "content": message.text}
            ]
        )
        reply = response.choices[0].message.content
        await message.answer(reply)
    except Exception as e:
        logging.error(f"Ошибка: {e}")
        await message.answer("Произошла ошибка при анализе. Попробуй позже.")

async def main():
    logging.info("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
