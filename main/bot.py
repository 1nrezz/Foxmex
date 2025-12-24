from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from config import BOT_TOKEN, ADMIN_USER_ID, model, BREAK
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest
import States
import db

bot = Bot(BOT_TOKEN)
dp = Dispatcher()

async def send_bot_answer(chat_id: int, answer_text: str, reply_to: int | None = None):
    if not answer_text:
        return

    try:
        await bot.send_message(chat_id=chat_id, text=answer_text, reply_to_message_id=reply_to)
    except TelegramBadRequest:
        await bot.send_message(chat_id=chat_id, text=answer_text)

async def is_group_admin(bot: Bot, chat_id: int, user_id: int) -> bool:
    member = await bot.get_chat_member(chat_id, user_id)
    return member.status in ("administrator", "creator")

async def is_admin(message: types.Message) -> bool:
    if message.chat.type == "private":
        return message.from_user.id == ADMIN_USER_ID
    else:
        return await is_group_admin(bot, message.chat.id, message.from_user.id)

@dp.message(Command("fix"))
async def fix_start(message: types.Message, state: FSMContext):
    if not await is_admin(message):
        return
    await message.answer(
        "Format:\n"
        "Question\n"
        f"{BREAK}\n"
        "New answer\n"
    )
    await state.set_state(States.FixFSM.waiting_for_text)


@dp.message(States.FixFSM.waiting_for_text)
async def fix_save(message: types.Message, state: FSMContext):
    if f"{BREAK}" not in message.text:
        await message.answer(f"⚠️ Invalid format, use 'Question {BREAK} Answer'")
        return

    before, after = message.text.split(f"{BREAK}", 1)
    question = before.strip()
    answer = after.strip()

    if not answer:
        await message.answer("❌ Answer is empty")
        await state.clear()
        return

    if not question:
        embedding = model.encode(answer).tolist()
        row = await db.find_best_answer(
            chat_id=message.chat.id,
            embedding=embedding,
            limit=0.0
        )
        if not row:
            await message.answer("❌ No question found for update")
            await state.clear()
            return
        question = row["question"]

    embedding = model.encode(question).tolist()
    await db.add_manual_knowledge(
        chat_id=message.chat.id,
        question=question,
        answer_text=answer,
        embedding=embedding
    )
    await message.answer("✅ Answer updated")
    await state.clear()

@dp.message(Command("add_question"))
async def add_question_start(message: types.Message, state: FSMContext):
    if not await is_admin(message):
        return
    await message.answer("Format:\n"
                         "Question\n"
                         f"{BREAK}\n"
                         "Answer\n"
                         )
    await state.set_state(States.AddQuestionFSM.waiting_for_text)


@dp.message(States.AddQuestionFSM.waiting_for_text)
async def add_question_save(message: types.Message, state: FSMContext):
    if f"{BREAK}" not in message.text:
        await message.answer(f"⚠️ Invalid format, use 'Question {BREAK} Answer'")
        return

    question, answer = map(str.strip, message.text.split(f"{BREAK}", 1))
    if not question or not answer:
        await message.answer("❌ The question or answer is empty")
        await state.clear()
        return

    embedding = model.encode(question).tolist()
    await db.add_manual_knowledge(
        chat_id=message.chat.id,
        question=question,
        answer_text=answer,
        embedding=embedding
    )
    await message.answer("✅ Question and answer added")
    await state.clear()

@dp.message(Command("delete_question"))
async def delete_question_start(message: types.Message, state: FSMContext):
    if not await is_admin(message):
        return
    await message.answer("Send the text of the question that needs to be deleted")
    await state.set_state(States.DeleteQuestionFSM.waiting_for_text)


@dp.message(States.DeleteQuestionFSM.waiting_for_text)
async def delete_question_confirm(message: types.Message, state: FSMContext):
    question_text = message.text.strip()
    embedding = model.encode(question_text).tolist()
    row = await db.find_best_answer(
        chat_id=message.chat.id,
        embedding=embedding,
        limit=0.0
    )
    if not row:
        await message.answer("❌ The question was not found in the database")
        await state.clear()
        return

    await db.delete_question(chat_id=message.chat.id, question=row["question"])
    await message.answer("🗑 Question and answer deleted")
    await state.clear()