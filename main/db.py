import asyncpg
from config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
import ast

from userbot import normalize

db_pool: asyncpg.Pool | None = None

async def init_db():
    global db_pool
    db_pool = await asyncpg.create_pool(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
    )

    async with db_pool.acquire() as conn:
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS knowledge (
            id SERIAL PRIMARY KEY,
            chat_id BIGINT,
            question_message_id BIGINT,
            question TEXT NOT NULL,
            answer_message_id BIGINT,
            answer_text TEXT,
            embedding VECTOR(384),
            source TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT NOW(),
            UNIQUE(chat_id, question)
        );
        """)
    print("✅ The database is ready")

def vector_to_str(embedding):
    if isinstance(embedding, str):
        embedding = ast.literal_eval(embedding)
    clean_embedding = [float(x) for x in embedding]
    return '[' + ','.join(f'{x:.6f}' for x in clean_embedding) + ']'

async def is_duplicate_embedding(chat_id, embedding, threshold=0.85):
    emb = vector_to_str(embedding)
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT 1 - cosine_distance(embedding, $1::vector) AS similarity
            FROM knowledge
            WHERE chat_id = $2 OR chat_id IS NULL
            ORDER BY similarity DESC
            LIMIT 1
        """, emb, chat_id)

    if row and row["similarity"] >= threshold:
        return True
    return False


async def add_group_knowledge(chat_id, question, question_message_id, embedding):
    if not question.strip():
        return

    if await is_duplicate_embedding(chat_id, embedding):
        return

    question_norm = normalize(question)
    emb = vector_to_str(embedding)

    async with db_pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO knowledge
            (chat_id, question, question_message_id, embedding, source)
            VALUES ($1, $2, $3, $4::vector, 'group')
        """, chat_id, question_norm, question_message_id, emb)

    print("✅ QUESTION SAVED:", question)

async def add_manual_knowledge(chat_id, question, answer_text, embedding):
    question_norm = normalize(question)
    emb = vector_to_str(embedding)
    async with db_pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO knowledge
            (chat_id, question, answer_text, embedding, source)
            VALUES ($1, $2, $3, $4::vector, 'manual')
            ON CONFLICT (chat_id, question) DO UPDATE
            SET answer_text = EXCLUDED.answer_text,
                embedding = EXCLUDED.embedding
        """, chat_id, question_norm, answer_text, emb)
        print(f"✅ Manual response added/updated: {question} (chat_id={chat_id})")

async def update_answer(chat_id, question_message_id, answer_text, answer_message_id):
    async with db_pool.acquire() as conn:
        result = await conn.execute("""
            UPDATE knowledge
            SET answer_text = $1,
                answer_message_id = $2
            WHERE chat_id = $3
              AND question_message_id = $4
        """, answer_text, answer_message_id, chat_id, question_message_id)

    if result.endswith("0"):
        print("⚠️ ANSWER IGNORED — QUESTION NOT FOUND")
    else:
        print("✅ ANSWER SAVED")

async def find_best_answer(chat_id, embedding, limit=0.75):
    emb = vector_to_str(embedding)
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT *,
                   1 - (embedding <=> $1) AS score
            FROM knowledge
            WHERE chat_id = $2 OR chat_id IS NULL
            ORDER BY source = 'manual' DESC, score DESC
            LIMIT 1
        """, emb, chat_id)

    if row and row["score"] >= limit:
        return row
    return None

async def delete_question(chat_id: int, question: str) -> bool:
    async with db_pool.acquire() as conn:
        result = await conn.execute("""
            DELETE FROM knowledge
            WHERE chat_id = $1
              AND question = $2
        """, chat_id, question)

    return not result.endswith("0")