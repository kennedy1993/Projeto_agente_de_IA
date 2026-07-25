import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
FONTE_DADOS_DIR = BASE_DIR / "fonte_de_dados"
VECTORSTORE_DIR = BASE_DIR / "vectorstore"

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

EMBEDDING_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"

CHUNK_SIZE = 800
CHUNK_OVERLAP = 150
TOP_K = 8
MIN_SIMILARITY = 0.3

EMPRESA_NOME = "BimBam Buy"
