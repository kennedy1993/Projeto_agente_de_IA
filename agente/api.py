"""API HTTP + interface web para conversar com o agente de suporte."""
import logging

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from agente import config, rag

MAX_MENSAGEM = 2000
MAX_HISTORICO = 6

logger = logging.getLogger("agente.api")
app = FastAPI(title="Agente de Suporte BimBam Buy")


class Mensagem(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=MAX_MENSAGEM)
    history: list[Mensagem] = Field(default_factory=list)


class ChatResponse(BaseModel):
    response: str
    sources: list[str]


def _sanitizar_historico(historico: list[Mensagem]) -> list[dict]:
    limpo = []
    for item in historico[-MAX_HISTORICO:]:
        if item.role not in ("user", "assistant"):
            continue
        limpo.append({"role": item.role, "content": item.content[:MAX_MENSAGEM]})
    return limpo


@app.on_event("startup")
def _warmup() -> None:
    rag.warmup()


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    historico = _sanitizar_historico(req.history)
    try:
        resposta, fontes = rag.ask(req.message, historico)
    except Exception:  # falha ao chamar a Groq, índice ausente etc.
        logger.exception("Falha ao gerar resposta do agente")
        raise HTTPException(
            status_code=502, detail="Erro ao gerar resposta. Tente novamente em instantes."
        ) from None
    fontes_unicas = sorted({f["source"] for f in fontes})
    return ChatResponse(response=resposta, sources=fontes_unicas)


app.mount("/", StaticFiles(directory=str(config.BASE_DIR / "static"), html=True), name="static")
