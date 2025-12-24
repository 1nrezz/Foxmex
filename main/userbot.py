from telethon import TelegramClient, events
import db
from config import API_ID, API_HASH, CHANNELS, model, WELCOME
import re
from bot import send_bot_answer, bot

client = TelegramClient("session", API_ID, API_HASH)

@client.on(events.ChatAction())
async def welcome_bot(event):
    if not (event.user_added or event.created):
        return
    me = await bot.get_me()
    if me.id in event.user_ids:
        chat_id = event.chat_id

        print(f"🤖 The bot has been added to the chat: {chat_id}")

        try:
            await bot.send_message(
                chat_id=chat_id,
                text=WELCOME["text"]
            )
            print(f"✅ Greeting sent to {chat_id}")
        except Exception as e:
            print(f"❌ Failed to send message: {e}")

def normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

async def resolve_source_channels(channels_raw):
    resolved = []
    for name in channels_raw:
        try:
            entity = await client.get_entity(name)
            resolved.append(entity.id)
        except Exception as e:
            print(f"⚠️ Failed to get ID for {name}: {e}")
    print(resolved)
    return resolved

async def process_old_messages(limit=1000):
    CHANNELS_ID = await resolve_source_channels(CHANNELS)
    for channel in CHANNELS_ID:
        async for message in client.iter_messages(channel, limit=limit):
            await process_message(message)

async def process_message(message):
    if not message.text:
        return

    text = message.text.strip()

    if message.reply_to_msg_id:
        original = await message.get_reply_message()
        if not original or not original.text:
            return

        await db.update_answer(
            chat_id=message.chat_id,
            question_message_id=original.id,
            answer_text=text,
            answer_message_id=message.id
        )
        print("✅ ANSWER SAVED")
        return

    if "?" not in text or len(text.split()) < 3:
        return

    question = normalize(text)
    embedding = model.encode(question).tolist()

    await db.add_group_knowledge(
        chat_id=message.chat_id,
        question=question,
        question_message_id=message.id,
        embedding=embedding
    )
    print("✅ QUESTION SAVED")

    answer = await db.find_best_answer(
        chat_id=message.chat_id,
        embedding=embedding
    )

    if answer and answer.get("answer_text"):
        await send_bot_answer(message.chat_id, answer["answer_text"], reply_to=message.id)


@client.on(events.NewMessage())
async def handler(event):
    await process_message(event.message)

async def start_userbot():
    await client.start()
    print("Userbot is ready, history is saved")
    await process_old_messages(1000)
    await client.run_until_disconnected()