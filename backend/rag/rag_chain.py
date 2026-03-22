# rag/rag_chain.py
# Builds a LangChain RetrievalQA chain with a domain-specific financial prompt.

import logging
from langchain_classic.chains import RetrievalQA
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from rag.retriever import get_retriever
from config import settings

logger = logging.getLogger(__name__)

PROMPT_TEMPLATE = """You are a financial research assistant. Use ONLY the context below to answer the question concisely.
If the answer is not in the context, say "I don't have that information in my knowledge base."
Do not cite sources inline — sources are handled separately.
Answer completely in one pass. Do not repeat points.

Context:
{context}

Question: {question}

Answer:"""


def get_rag_chain() -> RetrievalQA:
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
        openai_api_key=settings.openai_api_key,
    )
    prompt = PromptTemplate(
        template=PROMPT_TEMPLATE,
        input_variables=["context", "question"],
    )
    chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=get_retriever(),
        return_source_documents=True,
        chain_type_kwargs={"prompt": prompt},
    )
    logger.info("RAG chain initialised")
    return chain
