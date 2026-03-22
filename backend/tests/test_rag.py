# tests/test_rag.py
# Tests for the RAG pipeline.
# Test cases to implement:
#   - test_ingestion_creates_documents: ingest a small PDF and verify rows appear in Supabase
#   - test_retriever_returns_results: query the retriever and verify non-empty results
#   - test_rag_chain_answers: run a financial question through the chain and check the response
