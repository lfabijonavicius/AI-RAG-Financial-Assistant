# rag/ingestion.py
# Loads PDFs from data/raw/, chunks them, embeds with OpenAI, upserts to Supabase pgvector.

import logging
import uuid
import tempfile
import os
from pathlib import Path
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from db.supabase import supabase
from config import settings

logger = logging.getLogger(__name__)

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150


def load_documents(path: str):
    raw = Path(path)
    docs = []
    pdfs = list(raw.glob("*.pdf"))
    if not pdfs:
        logger.warning(f"No PDFs found in {path}")
        return docs
    for pdf in pdfs:
        logger.info(f"Loading {pdf.name}")
        loader = PyPDFLoader(str(pdf))
        docs.extend(loader.load())
    logger.info(f"Loaded {len(docs)} pages from {len(pdfs)} PDFs")
    return docs


def chunk_documents(docs):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )
    chunks = splitter.split_documents(docs)
    logger.info(f"Split into {len(chunks)} chunks")
    return chunks


UPSERT_BATCH_SIZE = 50  # small batches to avoid Supabase statement timeout


def get_ingested_sources() -> set[str]:
    """Return set of source file paths already in the documents table."""
    result = supabase.table("documents").select("metadata").execute()
    sources = set()
    for row in result.data:
        src = (row.get("metadata") or {}).get("source")
        if src:
            sources.add(src)
    return sources


def ingest_file(file_bytes: bytes, filename: str) -> int:
    """Ingest a single PDF from bytes. Stores source as 'pdfs/{filename}' for deduplication."""
    storage_source = f"pdfs/{filename}"
    already_ingested = get_ingested_sources()
    if storage_source in already_ingested:
        logger.info(f"{filename} already ingested — skipping")
        return 0

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    try:
        loader = PyPDFLoader(tmp_path)
        docs = loader.load()
        # Override source metadata to use stable storage path
        for doc in docs:
            doc.metadata["source"] = storage_source
    finally:
        os.unlink(tmp_path)

    if not docs:
        return 0

    chunks = chunk_documents(docs)
    embeddings = OpenAIEmbeddings(openai_api_key=settings.openai_api_key)

    for i in range(0, len(chunks), UPSERT_BATCH_SIZE):
        batch = chunks[i: i + UPSERT_BATCH_SIZE]
        texts = [c.page_content for c in batch]
        vectors = embeddings.embed_documents(texts)
        rows = [
            {"id": str(uuid.uuid4()), "content": text, "embedding": vector, "metadata": doc.metadata}
            for text, vector, doc in zip(texts, vectors, batch)
        ]
        supabase.table("documents").upsert(rows).execute()
        logger.info(f"Upserted batch {i // UPSERT_BATCH_SIZE + 1} ({len(batch)} chunks)")

    logger.info(f"Ingested {filename}: {len(chunks)} chunks")
    return len(chunks)


def delete_file_chunks(filename: str) -> None:
    """Remove all chunks for a given uploaded file from the documents table."""
    storage_source = f"pdfs/{filename}"
    supabase.table("documents").delete().eq("metadata->>source", storage_source).execute()
    logger.info(f"Deleted chunks for {filename}")


def ingest(path: str | None = None) -> int:
    """Load PDFs, chunk, embed and upsert to Supabase. Skips already-ingested files."""
    raw_path = path or settings.raw_data_path
    docs = load_documents(raw_path)
    if not docs:
        return 0

    already_ingested = get_ingested_sources()
    new_docs = [d for d in docs if d.metadata.get("source") not in already_ingested]
    if not new_docs:
        logger.info("All documents already ingested — nothing to do")
        return 0

    skipped = len(docs) - len(new_docs)
    if skipped:
        logger.info(f"Skipping {skipped} pages from already-ingested files")

    chunks = chunk_documents(new_docs)
    embeddings = OpenAIEmbeddings(openai_api_key=settings.openai_api_key)

    # Insert in small batches to avoid Supabase statement timeout
    for i in range(0, len(chunks), UPSERT_BATCH_SIZE):
        batch = chunks[i: i + UPSERT_BATCH_SIZE]
        texts = [c.page_content for c in batch]
        vectors = embeddings.embed_documents(texts)
        rows = [
            {
                "id": str(uuid.uuid4()),
                "content": text,
                "embedding": vector,
                "metadata": doc.metadata,
            }
            for text, vector, doc in zip(texts, vectors, batch)
        ]
        supabase.table("documents").upsert(rows).execute()
        logger.info(f"Upserted batch {i // UPSERT_BATCH_SIZE + 1} ({len(batch)} chunks)")

    logger.info(f"Upserted {len(chunks)} chunks to Supabase")
    return len(chunks)
