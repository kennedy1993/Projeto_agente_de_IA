"""Lê os PDFs em fonte_de_dados/, gera chunks e constrói o índice vetorial FAISS."""
import pickle

import faiss
import numpy as np
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer

from agente import config


def load_pdf_text(path) -> str:
    reader = PdfReader(str(path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if len(current) + len(paragraph) + 1 <= chunk_size:
            current = f"{current}\n{paragraph}".strip()
            continue
        if current:
            chunks.append(current)
        tail = chunks[-1][-overlap:] if chunks and overlap > 0 else ""
        current = f"{tail}\n{paragraph}".strip()
    if current:
        chunks.append(current)
    return chunks


def build_index() -> None:
    pdf_paths = sorted(config.FONTE_DADOS_DIR.glob("*.pdf"))
    if not pdf_paths:
        raise SystemExit(f"Nenhum PDF encontrado em {config.FONTE_DADOS_DIR}")

    all_chunks: list[dict] = []
    for pdf_path in pdf_paths:
        text = load_pdf_text(pdf_path)
        chunks = chunk_text(text, config.CHUNK_SIZE, config.CHUNK_OVERLAP)
        print(f"{pdf_path.name}: {len(chunks)} chunks")
        all_chunks.extend({"text": c, "source": pdf_path.name} for c in chunks)

    print(f"\nTotal de chunks: {len(all_chunks)}")
    print(f"Carregando modelo de embeddings ({config.EMBEDDING_MODEL_NAME})...")
    model = SentenceTransformer(config.EMBEDDING_MODEL_NAME)

    embeddings = model.encode(
        [c["text"] for c in all_chunks],
        normalize_embeddings=True,
        show_progress_bar=True,
    )
    embeddings = np.asarray(embeddings, dtype="float32")

    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings)

    config.VECTORSTORE_DIR.mkdir(exist_ok=True)
    # Serializa em memória em vez de faiss.write_index: o FAISS usa fopen em C
    # e falha com caminhos contendo caracteres não-ASCII (ex.: "AVANÇO").
    index_bytes = faiss.serialize_index(index)
    with open(config.VECTORSTORE_DIR / "index.faiss", "wb") as f:
        f.write(index_bytes.tobytes())
    with open(config.VECTORSTORE_DIR / "chunks.pkl", "wb") as f:
        pickle.dump(all_chunks, f)

    print(f"\nÍndice salvo em {config.VECTORSTORE_DIR}")


if __name__ == "__main__":
    build_index()
