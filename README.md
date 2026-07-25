# Agente de Suporte — BimBam Buy

Agente de IA que tira dúvidas de clientes (reembolso, garantia, envio, pagamentos,
programa de afiliados) com base nas políticas oficiais em `fonte_de_dados/`.

## Arquitetura

RAG simples e local:

1. `agente/ingest.py` lê os PDFs de `fonte_de_dados/`, quebra em chunks e gera
   embeddings (`sentence-transformers`, modelo multilíngue) salvos em `vectorstore/`
   (FAISS, local, sem serviço externo).
2. `agente/rag.py` busca os trechos mais relevantes para a pergunta do cliente e
   pede ao modelo da Groq (`llama-3.3-70b-versatile`) para responder **somente**
   com base nesses trechos.
3. Se nenhum trecho relevante for encontrado, o agente não inventa resposta —
   orienta o cliente a falar com o suporte humano.

## Configuração

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Copie `.env.example` para `.env` e preencha `GROQ_API_KEY` com uma chave de
https://console.groq.com.

## Uso (local, sem Docker)

```
# 1. Gerar o índice a partir dos PDFs (rodar de novo sempre que os PDFs mudarem)
python -m agente.ingest

# 2a. Conversar com o agente no terminal
python -m agente.chat_cli

# 2b. Ou subir a interface web (http://localhost:8000)
uvicorn agente.api:app --reload
```

## Uso com Docker

O índice vetorial é gerado durante o `docker build` (a base de conhecimento é
estática), então o container sobe já pronto para responder.

```
docker compose up -d --build
```

Interface web em http://localhost:8080. O `docker-compose.yml` lê a
`GROQ_API_KEY` do arquivo `.env` local (nunca é copiada para dentro da imagem —
veja `.dockerignore`).

Se mudar algum PDF em `fonte_de_dados/`, rode `docker compose up -d --build`
de novo para regerar o índice.

## Limitações conhecidas

- As respostas ficam tão precisas quanto os PDFs de origem: se uma política não
  tem um número exato (ex.: prazo de pagamento de comissão "conforme calendário
  interno"), o agente não vai inventar um número — vai dizer que não tem o dado
  exato e sugerir o suporte humano. Isso é intencional (evita prometer prazo,
  valor ou garantia errados).
- `TOP_K` e `MIN_SIMILARITY` (em `agente/config.py`) controlam quantos trechos
  entram no contexto e o quão relevantes eles precisam ser. Ajuste se notar
  respostas incompletas ou contexto irrelevante.
