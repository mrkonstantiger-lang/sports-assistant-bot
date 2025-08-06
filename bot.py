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
ASSISTANT_ID = os.getenv("OPENAI_ASSISTANT_ID")

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Настройка OpenAI
openai.api_key = OPENAI_API_KEY

# Инициализация бота
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Словарь для хранения потоков пользователей
user_threads = {}

@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    await message.answer("Привет! Я готов отвечать на твои вопросы.")

@dp.message()
async def handle_message(message: types.Message):
    user_id = str(message.from_user.id)

    if user_id not in user_threads:
        thread = openai.beta.threads.create()
        user_threads[user_id] = thread.id

    try:
        # Отправляем сообщение пользователя в поток
        openai.beta.threads.messages.create(
            thread_id=user_threads[user_id],
            role="user",
            content=message.text
        )

        # Запускаем ассистента
        run = openai.beta.threads.runs.create(
            thread_id=user_threads[user_id],
            assistant_id=ASSISTANT_ID
        )

        # Ждем завершения обработки
        while True:
            run_status = openai.beta.threads.runs.retrieve(
                thread_id=user_threads[user_id],
                run_id=run.id
            )
            if run_status.status == "completed":
                break
            await asyncio.sleep(1)

        # Получаем ответ ассистента
        messages = openai.beta.threads.messages.list(
            thread_id=user_threads[user_id]
        )
        reply = messages.data[0].content[0].text.value
        await message.answer(reply)

    except Exception as e:
        logging.error(f"Ошибка: {e}")
        await message.answer("Произошла ошибка при анализе. Попробуй позже.")

async def main():
    logging.info("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
