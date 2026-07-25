"""Recuperação de contexto (RAG) + geração de resposta via Groq."""
import pickle

import faiss
import numpy as np
from groq import Groq
from sentence_transformers import SentenceTransformer

from agente import config

SYSTEM_PROMPT = f"""Você é o assistente de suporte da {config.EMPRESA_NOME}, um e-commerce.
Seu único trabalho é tirar dúvidas de clientes usando os trechos de política oficial
fornecidos abaixo, na seção "Trechos relevantes".

Tom de voz da marca: amigável, dinâmico, claro, próximo, com um toque divertido,
mas sem perder o profissionalismo.

Regras obrigatórias:
- Responda SOMENTE com base nos trechos fornecidos. Nunca invente prazos, valores,
  políticas ou exceções que não estejam no contexto.
- Se o contexto não tiver a resposta, diga claramente que não tem essa informação
  e oriente o cliente a falar com o suporte humano. Não tente adivinhar.
- Nunca prometa reembolsos, prazos de envio, garantias ou valores de comissão fora
  do que está escrito no contexto.
- Seja direto e objetivo; evite parágrafos longos.
- Responda sempre em português do Brasil.
"""

_model: SentenceTransformer | None = None
_index: faiss.Index | None = None
_chunks: list[dict] | None = None
_client: Groq | None = None


def _load() -> None:
    global _model, _index, _chunks, _client
    if _model is not None:
        return
    if not (config.VECTORSTORE_DIR / "index.faiss").exists():
        raise SystemExit(
            "Índice não encontrado. Rode primeiro: python -m agente.ingest"
        )
    _model = SentenceTransformer(config.EMBEDDING_MODEL_NAME)
    # Lê os bytes em Python puro e desserializa: faiss.read_index usa fopen em
    # C, que falha com caminhos contendo caracteres não-ASCII (ex.: "AVANÇO").
    with open(config.VECTORSTORE_DIR / "index.faiss", "rb") as f:
        index_bytes = np.frombuffer(f.read(), dtype="uint8")
    _index = faiss.deserialize_index(index_bytes)
    with open(config.VECTORSTORE_DIR / "chunks.pkl", "rb") as f:
        _chunks = pickle.load(f)
    if not config.GROQ_API_KEY:
        raise SystemExit("GROQ_API_KEY não definido. Configure o arquivo .env.")
    _client = Groq(api_key=config.GROQ_API_KEY)


def retrieve(query: str, top_k: int = config.TOP_K) -> list[dict]:
    _load()
    q_emb = _model.encode([query], normalize_embeddings=True)
    q_emb = np.asarray(q_emb, dtype="float32")
    scores, idx = _index.search(q_emb, top_k)
    results = []
    for score, i in zip(scores[0], idx[0]):
        if i == -1:
            continue
        results.append({**_chunks[i], "score": float(score)})
    return results


def _build_messages(query: str, contexto: list[dict], historico: list[dict]) -> list[dict]:
    context_block = "\n\n".join(
        f"[Fonte: {c['source']}]\n{c['text']}" for c in contexto
    )
    system = f"{SYSTEM_PROMPT}\nTrechos relevantes:\n{context_block}"
    messages = [{"role": "system", "content": system}]
    messages.extend(historico)
    messages.append({"role": "user", "content": query})
    return messages


def warmup() -> None:
    _load()


def ask(query: str, historico: list[dict] | None = None) -> tuple[str, list[dict]]:
    _load()
    historico = (historico or [])[-6:]

    contexto = retrieve(query)
    relevante = [c for c in contexto if c["score"] >= config.MIN_SIMILARITY]

    if not relevante:
        resposta = (
            "Não encontrei essa informação nas nossas políticas oficiais. "
            "Para não te passar um dado incorreto, recomendo falar com o nosso "
            "time de suporte humano, que pode analisar seu caso com mais detalhe."
        )
        return resposta, []

    messages = _build_messages(query, relevante, historico)
    completion = _client.chat.completions.create(
        model=config.GROQ_MODEL,
        messages=messages,
        temperature=0.3,
        max_tokens=600,
    )
    resposta = completion.choices[0].message.content
    return resposta, relevante
