# rag/retriever.py
# Custom retriever that calls match_documents RPC directly.
# Bypasses langchain-community SupabaseVectorStore which is incompatible with supabase-py 2.x.
# Also provides TracedMultiQueryRetriever which captures generated queries and retrieved
# chunks into a ContextVar so the stream handler can expose them to the frontend.

import logging
from contextvars import ContextVar
from langchain_core.retrievers import BaseRetriever
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from db.supabase import supabase
from config import settings

logger = logging.getLogger(__name__)

# Per-request store for RAG process data (queries + retrieved chunks).
# Scoped to asyncio Tasks so concurrent requests don't interfere.
rag_process_data: ContextVar[dict] = ContextVar("rag_process_data", default={})

TOP_K = 10


class SupabaseRetriever(BaseRetriever):
    """Calls match_documents RPC directly — compatible with supabase-py 2.x."""

    top_k: int = TOP_K
    source_filter: str = ""

    def _get_relevant_documents(self, query: str) -> list[Document]:
        embeddings = OpenAIEmbeddings(openai_api_key=settings.openai_api_key)
        query_vector = embeddings.embed_query(query)

        # Fetch extra when filtering so we still get top_k after narrowing
        fetch_count = self.top_k * 4 if self.source_filter else self.top_k
        result = supabase.rpc(
            "match_documents",
            {"query_embedding": query_vector, "match_count": fetch_count},
        ).execute()

        docs = []
        for row in result.data:
            source = row.get("metadata", {}).get("source", "unknown")
            if self.source_filter and self.source_filter.lower() not in source.lower():
                continue
            docs.append(Document(
                page_content=row["content"],
                metadata={"source": source, "similarity": row.get("similarity")},
            ))
        docs = docs[:self.top_k]
        logger.info(f"Retrieved {len(docs)} documents for query (filter={self.source_filter!r})")
        return docs


def get_retriever(top_k: int = TOP_K, source_filter: str = "") -> SupabaseRetriever:
    return SupabaseRetriever(top_k=top_k, source_filter=source_filter)


from pydantic import PrivateAttr
from langchain_classic.retrievers.multi_query import MultiQueryRetriever
from langchain_core.callbacks import CallbackManagerForRetrieverRun


class TracedMultiQueryRetriever(MultiQueryRetriever):
    """Subclass of MultiQueryRetriever that stores generated queries and
    retrieved chunks as private instance attributes so they can be read
    by the tool function after invocation — no ContextVar needed."""

    _last_queries: list = PrivateAttr(default_factory=list)
    _last_chunks: list = PrivateAttr(default_factory=list)

    def generate_queries(self, question: str, run_manager: CallbackManagerForRetrieverRun) -> list[str]:
        queries = super().generate_queries(question, run_manager)
        self._last_queries = list(queries)
        return queries

    def unique_union(self, documents: list[Document]) -> list[Document]:
        unique_docs = super().unique_union(documents)
        self._last_chunks = [
            {
                "content": d.page_content[:300],
                "source": d.metadata.get("source", "unknown").split("/")[-1],
                "similarity": d.metadata.get("similarity"),
            }
            for d in unique_docs
        ]
        logger.info(f"TracedMultiQueryRetriever: {len(self._last_queries)} queries, {len(unique_docs)} unique chunks")
        return unique_docs
