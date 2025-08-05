import logging
import openai
import asyncio
import os
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ASSISTANT_ID = os.getenv("OPENAI_ASSISTANT_ID")

openai.api_key = OPENAI_API_KEY
logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

user_threads = {}

@dp.message()
async def handle_message(message: Message):
    user_id = str(message.from_user.id)

    if user_id not in user_threads:
        thread = openai.beta.threads.create()
        user_threads[user_id] = thread.id

    try:
        openai.beta.threads.messages.create(
            thread_id=user_threads[user_id],
            role="user",
            content=message.text
        )

        run = openai.beta.threads.runs.create(
            thread_id=user_threads[user_id],
            assistant_id=ASSISTANT_ID
        )

        while True:
            run_status = openai.beta.threads.runs.retrieve(
                thread_id=user_threads[user_id],
                run_id=run.id
            )
            if run_status.status == "completed":
                break
            await asyncio.sleep(1)

        messages = openai.beta.threads.messages.list(
            thread_id=user_threads[user_id]
        )
        reply = messages.data[0].content[0].text.value
        await message.answer(reply)

    except Exception as e:
        logging.error(f"Ошибка: {e}")
        await message.answer("Произошла ошибка при анализе. Попробуй позже.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    start_webhook(
        dispatcher=dp,
        webhook_path=WEBHOOK_PATH,
        on_startup=on_startup,
        on_shutdown=on_shutdown,
        host=WEBAPP_HOST,
        port=WEBAPP_PORT,
    )

