import os
import json
from dotenv import load_dotenv

with open("welcome.json", "r", encoding="utf-8") as f:
    WELCOME = json.load(f)

os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
from sentence_transformers import SentenceTransformer
model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

load_dotenv()

BOT_TOKEN = os.getenv("TOKEN")
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = int(os.getenv("DB_PORT"))

ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID"))

CHANNELS = ["foxmex"]

BREAK = "###"

