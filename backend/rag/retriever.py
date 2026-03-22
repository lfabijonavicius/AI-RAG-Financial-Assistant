# rag/retriever.py
# Custom retriever that calls match_documents RPC directly.
# Bypasses langchain-community SupabaseVectorStore which is incompatible with supabase-py 2.x.

import logging
from langchain_core.retrievers import BaseRetriever
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from db.supabase import supabase
from config import settings

logger = logging.getLogger(__name__)

TOP_K = 4


class SupabaseRetriever(BaseRetriever):
    """Calls match_documents RPC directly — compatible with supabase-py 2.x."""

    def _get_relevant_documents(self, query: str) -> list[Document]:
        embeddings = OpenAIEmbeddings(openai_api_key=settings.openai_api_key)
        query_vector = embeddings.embed_query(query)

        result = supabase.rpc(
            "match_documents",
            {"query_embedding": query_vector, "match_count": TOP_K},
        ).execute()

        docs = []
        for row in result.data:
            docs.append(Document(
                page_content=row["content"],
                metadata={"source": row.get("metadata", {}).get("source", "unknown"), "similarity": row.get("similarity")},
            ))
        logger.info(f"Retrieved {len(docs)} documents for query")
        return docs


def get_retriever() -> SupabaseRetriever:
    return SupabaseRetriever()
