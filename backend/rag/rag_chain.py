# rag/rag_chain.py
# Builds a LangChain RetrievalQA chain with a domain-specific financial prompt.
# Uses MultiQueryRetriever: rewrites the user's question into multiple variants
# before searching, so semantically different phrasings of the same question
# all retrieve relevant chunks.

import logging
from langchain_classic.chains import RetrievalQA
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from rag.retriever import get_retriever, TracedMultiQueryRetriever
from config import settings

logger = logging.getLogger(__name__)

PROMPT_TEMPLATE = """You are a financial research assistant. Answer using ONLY the information in the context below.
Rules:
- Base your answer entirely on the context. Do not use outside knowledge.
- If the answer genuinely cannot be found in the context, say "I don't have that information in my knowledge base."
- Do not cite sources inline — sources are handled separately.
- Answer completely in one pass. Do not repeat points.

Context:
{context}

Question: {question}

Answer:"""


def get_rag_chain(source_filter: str = "") -> RetrievalQA:
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
        openai_api_key=settings.openai_api_key,
    )

    # MultiQueryRetriever wraps the base retriever:
    # 1. LLM generates 3 alternative phrasings of the user's question
    # 2. Each phrasing is searched independently against the vector DB
    # 3. Results are deduplicated and combined before being passed to the LLM
    base_retriever = get_retriever(source_filter=source_filter)
    multi_retriever = TracedMultiQueryRetriever.from_llm(
        retriever=base_retriever,
        llm=llm,
    )

    prompt = PromptTemplate(
        template=PROMPT_TEMPLATE,
        input_variables=["context", "question"],
    )
    chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=multi_retriever,
        return_source_documents=True,
        chain_type_kwargs={"prompt": prompt},
    )
    logger.info("RAG chain initialised with MultiQueryRetriever")
    return chain
