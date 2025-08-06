import logging
import os
import asyncio
import openai
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
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
    asyncio.run(main())


        messages = openai.beta.threads.messages.list(
            thread_id=user_threads[user_id]
        )
        reply = messages.data[0].content[0].text.value
        await message.answer(reply)

    except Exception as e:
        logging.error(f"Ошибка: {e}")
        await message.answer("Произошла ошибка при анализе. Попробуй позже.")

async def on_startup():
    await bot.set_webhook(WEBHOOK_URL)
    logging.info(f"Webhook установлен: {WEBHOOK_URL}")

async def on_shutdown():
    await bot.delete_webhook()
    logging.info("Webhook удалён")

async def main():
    await on_startup()
    await dp.start_webhook(
        webhook_path=WEBHOOK_PATH,
        host=WEBAPP_HOST,
        port=WEBAPP_PORT,
        on_shutdown=on_shutdown,
    )

if __name__ == "__main__":
    asyncio.run(main())
