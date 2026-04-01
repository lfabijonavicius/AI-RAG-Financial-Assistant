# rag/ingestion.py
# Handles the full PDF → vector database pipeline.
# Steps: load PDF → split into chunks → generate embeddings → store in Supabase pgvector.
# Supports both bulk ingestion (from a local folder) and single-file upload ingestion.

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

# Chunk size controls how much text each vector represents.
# Smaller chunks = more precise retrieval but more vectors to store and search.
# Overlap ensures sentences aren't cut off at chunk boundaries.
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150

# Small batches prevent Supabase from timing out on large inserts
UPSERT_BATCH_SIZE = 50


def load_documents(path: str):
    """Load all PDF files from a local directory using LangChain's PDF loader."""
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
    """Split documents into overlapping chunks for vector search.
    RecursiveCharacterTextSplitter tries to break at natural boundaries
    (paragraphs, sentences) before falling back to character splits."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )
    chunks = splitter.split_documents(docs)
    logger.info(f"Split into {len(chunks)} chunks")
    return chunks


def get_ingested_sources() -> set[str]:
    """Return the set of source file paths already stored in the documents table.
    Used to skip re-ingesting files that haven't changed."""
    result = supabase.table("documents").select("metadata").execute()
    sources = set()
    for row in result.data:
        src = (row.get("metadata") or {}).get("source")
        if src:
            sources.add(src)
    return sources


def ingest_file(file_bytes: bytes, filename: str) -> int:
    """Ingest a single PDF uploaded via the API.
    Writes to a temp file (PyPDFLoader needs a file path, not bytes),
    then chunks, embeds and upserts to Supabase. Skips if already ingested."""
    storage_source = f"pdfs/{filename}"

    # Skip if this file was already ingested — avoids duplicate vectors
    already_ingested = get_ingested_sources()
    if storage_source in already_ingested:
        logger.info(f"{filename} already ingested — skipping")
        return 0

    # Write bytes to a temp file so PyPDFLoader can open it
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    try:
        loader = PyPDFLoader(tmp_path)
        docs = loader.load()
        # Override the default source path with the stable Supabase Storage path
        for doc in docs:
            doc.metadata["source"] = storage_source
    finally:
        os.unlink(tmp_path)  # Always clean up the temp file

    if not docs:
        return 0

    chunks = chunk_documents(docs)
    embeddings = OpenAIEmbeddings(openai_api_key=settings.openai_api_key)

    # Embed and upsert in batches to stay within Supabase's statement size limits
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
    """Remove all vector chunks belonging to a specific uploaded file.
    Called when a user deletes a document from the knowledge base."""
    storage_source = f"pdfs/{filename}"
    supabase.table("documents").delete().eq("metadata->>source", storage_source).execute()
    logger.info(f"Deleted chunks for {filename}")


def ingest(path: str | None = None) -> int:
    """Bulk ingestion from a local folder — used for initial data loading.
    Automatically skips any files that are already in the vector database."""
    raw_path = path or settings.raw_data_path
    docs = load_documents(raw_path)
    if not docs:
        return 0

    # Filter out pages from files we've already processed
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
