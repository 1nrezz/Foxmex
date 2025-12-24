import db
import asyncio
from aiogram.types import BotCommand
from bot import bot, dp
from userbot import start_userbot

async def set_commands(bot):
    commands = [
        BotCommand(command="fix", description="Correct the bot's wrong answer in private chat"),
        BotCommand(command="add_question", description="Add a new question and answer"),
        BotCommand(command="delete_question", description="Delete a question and answer"),
    ]
    await bot.set_my_commands(commands)

async def main():
    await db.init_db()
    asyncio.create_task(start_userbot())

    await set_commands(bot)
    try:
        await dp.start_polling(bot)
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        await bot.session.close()
        print("The bot session has been closed")

asyncio.run(main())