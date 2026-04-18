# rag/rag_chain.py
# Builds the Retrieval-Augmented Generation (RAG) chain.
# RAG = retrieval + generation: instead of answering from training data,
# the LLM is given relevant document chunks as context and answers from those.
#
# Uses MultiQueryRetriever which improves recall by rephrasing the question
# into 3 variants before searching — catches more relevant chunks.

import logging
from langchain_classic.chains import RetrievalQA
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from rag.retriever import get_retriever, TracedMultiQueryRetriever
from config import settings

# Prompt that generates 2 query variants instead of the default 3.
# Fewer variants = fewer LLM calls = faster retrieval with minimal quality loss.
MULTI_QUERY_PROMPT = PromptTemplate(
    input_variables=["question"],
    template=(
        "Generate 2 different phrasings of the following question to improve "
        "document retrieval. Output only the questions, one per line, no numbering.\n\n"
        "Question: {question}"
    ),
)

logger = logging.getLogger(__name__)

# Strict prompt — forces the LLM to answer only from the retrieved context,
# not from its general training knowledge. This is essential for document Q&A accuracy.
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
    """Build and return a RetrievalQA chain.

    source_filter: if provided, only search chunks from documents matching this string.
    For example, source_filter='amazon' restricts retrieval to Amazon's uploaded files.
    A new chain is created per call so the retriever can carry the correct filter."""

    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,        # Temperature 0 = deterministic, factual answers
        openai_api_key=settings.openai_api_key,
    )

    # Separate lightweight LLM just for query generation — capped at 100 tokens
    # since the rephrased queries are always short. Saves ~1-2s vs using the full LLM.
    query_llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
        max_tokens=100,
        openai_api_key=settings.openai_api_key,
    )

    # MultiQueryRetriever improves retrieval quality by generating query variants:
    # 1. LLM rephrases the question (catches different wordings in the docs)
    # 2. Each variant is searched independently in the vector DB
    # 3. Results are merged and deduplicated before being passed to the answer LLM
    base_retriever = get_retriever(source_filter=source_filter)
    multi_retriever = TracedMultiQueryRetriever.from_llm(
        retriever=base_retriever,
        llm=query_llm,
        prompt=MULTI_QUERY_PROMPT,
    )

    prompt = PromptTemplate(
        template=PROMPT_TEMPLATE,
        input_variables=["context", "question"],
    )

    # "stuff" chain type = concatenate all chunks into one context string.
    # Good for gpt-4o-mini's large context window; would need "map_reduce" for very long docs.
    chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=multi_retriever,
        return_source_documents=True,   # Needed to show source filenames in the response
        chain_type_kwargs={"prompt": prompt},
    )

    logger.info("RAG chain initialised with MultiQueryRetriever")
    return chain
