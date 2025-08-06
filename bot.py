import logging
import os
import sys
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

lockfile = "bot.lock"

# Проверяем, запущен ли уже бот
if os.path.exists(lockfile):
    print("Бот уже запущен! Завершаем запуск.")
    sys.exit(1)
else:
    # Создаём lockfile, чтобы заблокировать повторный запуск
    open(lockfile, 'w').close()

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    await message.answer("Привет! Я готов отвечать на твои вопросы.")

@dp.message()
async def handle_message(message: types.Message):
    try:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": message.text}]
        )
        reply = response.choices[0].message.content
        await message.answer(reply)

    except Exception as e:
        logging.error(f"Ошибка: {e}")
        await message.answer("Произошла ошибка при анализе. Попробуй позже.")

async def main():
    try:
        logging.info("Бот запущен...")
        await dp.start_polling(bot)
    finally:
        # Удаляем lockfile при выходе из программы
        if os.path.exists(lockfile):
            os.remove(lockfile)

if __name__ == "__main__":
    asyncio.run(main())
