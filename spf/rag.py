"""Step 4: the RAG chain, written in LangChain Expression Language (LCEL).

    question
       |--> retriever (semantic search + price/rating filters) --> context
       |--> passthrough --------------------------------------> question
                     \\                                         /
                      ---> prompt ---> LLM ---> string answer

If no LLM is configured, the last two steps are replaced by a template that
lists the retrieved products, so the pipeline still runs end to end.
"""
from __future__ import annotations

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda, RunnableParallel, RunnablePassthrough

from . import config
from .llm import get_llm
from .search import Hit

SYSTEM = """You are a helpful shopping assistant for an online store.
Recommend products ONLY from the catalog context below. Never invent products,
prices or features. If nothing in the context fits, say so honestly.
For each pick give: product name, price in rupees, and one line on why it fits
the customer's need. Recommend at most 3 products, best first. Be brief.

Catalog context:
{context}"""

PROMPT = ChatPromptTemplate.from_messages([("system", SYSTEM), ("human", "{question}")])


def format_hits(hits: list[Hit]) -> str:
    blocks = []
    for i, h in enumerate(hits, 1):
        price = h.metadata.get("price", -1)
        rating = h.metadata.get("rating", -1)
        blocks.append(
            f"[{i}] {h.text}\nPrice: {'₹%d' % price if price >= 0 else 'not listed'}"
            f" | Rating: {rating if rating >= 0 else 'n/a'}"
        )
    return "\n\n".join(blocks)


def _template_answer(inputs: dict) -> str:
    hits: list[Hit] = inputs["hits"]
    if not hits:
        return "Sorry, I couldn't find a matching product in the catalog."
    lines = [f"Top matches for \"{inputs['question']}\":"]
    for h in hits[:3]:
        p = h.metadata.get("price", -1)
        lines.append(f"- {h.name} ({'₹%d' % p if p >= 0 else 'price n/a'}), match score {h.score:.2f}")
    lines.append("(Set SPF_LLM to anthropic/openai/ollama for a written recommendation.)")
    return "\n".join(lines)


def build_rag_chain(searcher, llm="auto", k: int = config.TOP_K):
    """Returns a Runnable: {"question": str} -> {"answer": str, "hits": [Hit]}"""
    if llm == "auto":
        llm = get_llm()

    retrieve = RunnableLambda(lambda q: searcher.search(q, k=k))

    gather = RunnableParallel(hits=retrieve, question=RunnablePassthrough())

    if llm is None:
        answer = RunnableLambda(_template_answer)
    else:
        answer = (
            RunnableLambda(lambda x: {"context": format_hits(x["hits"]), "question": x["question"]})
            | PROMPT
            | llm
            | StrOutputParser()
        )

    # input: question string -> gather hits -> add answer, keep hits for the UI
    return (
        RunnableLambda(lambda x: x["question"] if isinstance(x, dict) else x)
        | gather
        | RunnablePassthrough.assign(answer=answer)
    )
