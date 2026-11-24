"""End-to-end tests. Builds a fresh index in a temp dir (needs the embedding
model, downloaded automatically on first run)."""
import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel

from spf import config


@pytest.fixture(scope="module")
def engine(tmp_path_factory):
    config.CHROMA_DIR = tmp_path_factory.mktemp("chroma")
    from spf.engine import Engine
    from spf.vectorstore import build_vectorstore

    e = Engine()
    build_vectorstore(e.chunks)
    return e


def types(hits):
    return [h.metadata["type_id"] for h in hits]


def test_keyword_query_all_methods(engine):
    for mode in ["keyword", "bm25", "semantic", "hybrid"]:
        assert "yoga_mat" in types(engine.search("yoga mat", mode=mode, k=3)), mode


def test_semantic_beats_keyword_on_paraphrase(engine):
    q = "something to keep my coffee hot on the drive to work"
    assert types(engine.search(q, mode="semantic", k=1)) == ["insulated_tumbler"]
    assert "insulated_tumbler" not in types(engine.search(q, mode="keyword", k=5))


def test_price_filter_applied_in_vector_db(engine):
    hits = engine.search("bluetooth speaker under 2000", mode="semantic", k=5)
    assert hits and all(0 <= h.metadata["price"] <= 2000 for h in hits)


def test_rag_chain_without_llm(engine):
    from spf.rag import build_rag_chain

    out = build_rag_chain(engine.searchers["semantic"], llm=None).invoke({"question": "yoga mat"})
    assert "Yoga Mat" in out["answer"] and out["hits"]


def test_rag_chain_with_llm_gets_context(engine):
    from spf.rag import build_rag_chain

    llm = FakeListChatModel(responses=["Get the yoga mat."])
    chain = build_rag_chain(engine.searchers["semantic"], llm=llm)
    out = chain.invoke({"question": "mat for yoga"})
    assert out["answer"] == "Get the yoga mat."
    assert out["hits"][0].metadata["type_id"] == "yoga_mat"


def test_prompt_contains_retrieved_products(engine):
    from spf.rag import PROMPT, format_hits

    hits = engine.search("yoga mat", mode="semantic", k=2)
    msgs = PROMPT.format_messages(context=format_hits(hits), question="yoga mat")
    assert "Yoga Mat" in msgs[0].content and "Price: ₹" in msgs[0].content
