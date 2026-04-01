# rag/retriever.py
# Custom retriever that queries Supabase pgvector for semantically similar chunks.
# We bypass LangChain's built-in SupabaseVectorStore because it's incompatible
# with supabase-py v2. Instead we call the match_documents RPC directly.
#
# Also defines TracedMultiQueryRetriever — a subclass that captures the generated
# queries and retrieved chunks so the frontend can display them in the RAG process card.

import logging
from pydantic import PrivateAttr
from contextvars import ContextVar
from langchain_core.retrievers import BaseRetriever
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_classic.retrievers.multi_query import MultiQueryRetriever
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from db.supabase import supabase
from config import settings

logger = logging.getLogger(__name__)

# Per-request store for RAG process data — not currently used but kept for future use
rag_process_data: ContextVar[dict] = ContextVar("rag_process_data", default={})

TOP_K = 10  # Number of chunks to return per query


class SupabaseRetriever(BaseRetriever):
    """Calls the match_documents Supabase RPC to find the most similar chunks
    to a query using cosine similarity on OpenAI embeddings.

    source_filter: if set, only return chunks from documents whose source path
    contains this string (e.g. 'amazon' filters to Amazon's 10-K only).
    We fetch extra chunks before filtering to ensure we still get top_k results."""

    top_k: int = TOP_K
    source_filter: str = ""  # Optional — restricts results to a specific document

    def _get_relevant_documents(self, query: str) -> list[Document]:
        # Convert the query text into a vector using the same model used at ingestion time
        embeddings = OpenAIEmbeddings(openai_api_key=settings.openai_api_key)
        query_vector = embeddings.embed_query(query)

        # Fetch more chunks than needed when filtering so we have enough after narrowing
        fetch_count = self.top_k * 4 if self.source_filter else self.top_k

        result = supabase.rpc(
            "match_documents",
            {"query_embedding": query_vector, "match_count": fetch_count},
        ).execute()

        docs = []
        for row in result.data:
            source = row.get("metadata", {}).get("source", "unknown")
            # Skip chunks from other documents if a source filter is active
            if self.source_filter and self.source_filter.lower() not in source.lower():
                continue
            docs.append(Document(
                page_content=row["content"],
                metadata={"source": source, "similarity": row.get("similarity")},
            ))

        docs = docs[:self.top_k]  # Trim back to the requested limit
        logger.info(f"Retrieved {len(docs)} documents for query (filter={self.source_filter!r})")
        return docs


def get_retriever(top_k: int = TOP_K, source_filter: str = "") -> SupabaseRetriever:
    return SupabaseRetriever(top_k=top_k, source_filter=source_filter)


class TracedMultiQueryRetriever(MultiQueryRetriever):
    """Extends MultiQueryRetriever to record the generated sub-queries and
    retrieved chunks as private attributes after each retrieval.

    MultiQueryRetriever works by:
    1. Asking the LLM to rephrase the user's question in 3 different ways
    2. Running each rephrasing as a separate vector search
    3. Merging and deduplicating the results

    The traced version stores these internals so they can be shown in the UI."""

    _last_queries: list = PrivateAttr(default_factory=list)   # Generated sub-queries
    _last_chunks: list = PrivateAttr(default_factory=list)    # Retrieved chunks with metadata

    def generate_queries(self, question: str, run_manager: CallbackManagerForRetrieverRun) -> list[str]:
        """Intercept the generated queries so we can expose them in the frontend."""
        queries = super().generate_queries(question, run_manager)
        self._last_queries = list(queries)
        return queries

    def unique_union(self, documents: list[Document]) -> list[Document]:
        """Intercept the final deduplicated chunk list so we can show it in the UI."""
        unique_docs = super().unique_union(documents)
        self._last_chunks = [
            {
                "content": d.page_content[:300],   # Truncate for display
                "source": d.metadata.get("source", "unknown").split("/")[-1],
                "similarity": d.metadata.get("similarity"),
            }
            for d in unique_docs
        ]
        logger.info(f"TracedMultiQueryRetriever: {len(self._last_queries)} queries, {len(unique_docs)} unique chunks")
        return unique_docs
