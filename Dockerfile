FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HUB_DISABLE_SYMLINKS_WARNING=1

COPY requirements.txt .
# Instala o torch CPU-only antes do resto: sem isso, o pip puxa a build com
# CUDA (vários GB de pacotes nvidia-*) mesmo rodando só em CPU na nuvem.
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir -r requirements.txt

COPY agente/ agente/
COPY fonte_de_dados/ fonte_de_dados/
COPY static/ static/

# Gera o índice vetorial em tempo de build: a base de conhecimento (PDFs) é
# estática, então não precisa ser recalculada a cada início do container.
RUN python -m agente.ingest

EXPOSE 8000

CMD ["uvicorn", "agente.api:app", "--host", "0.0.0.0", "--port", "8000"]
