"""Step 1 of the pipeline: load the messy CSV, clean it, turn rows into
LangChain `Document`s, and split long ones into chunks.

    raw CSV  ->  clean DataFrame  ->  Documents  ->  chunks (ready to embed)
"""
from __future__ import annotations

import html
import re
from pathlib import Path

import pandas as pd
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from . import config

_TAG_RE = re.compile(r"<[^>]+>")
_SPEC_RE = re.compile(r'"key"=>"(.*?)",\s*"value"=>"(.*?)"')
_NUM_RE = re.compile(r"\d+(?:\.\d+)?")


# ---------- small cleaning helpers (each one is unit tested) ----------

def parse_price(raw) -> float | None:
    """'₹1,299' / 'Rs. 1299' / 'INR 1,299' / '1299.00' -> 1299.0 ; '' -> None"""
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return None
    s = str(raw).replace(",", "")
    m = _NUM_RE.search(s)
    return float(m.group()) if m else None


def clean_text(raw) -> str:
    """Remove HTML tags/entities and squash whitespace."""
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return ""
    s = html.unescape(str(raw))
    s = _TAG_RE.sub(" ", s)
    return re.sub(r"\s+", " ", s).strip()


def parse_specs(raw) -> dict[str, str]:
    """Flipkart-style '{"key"=>"Battery", "value"=>"30 hours"}' blob -> dict."""
    if not isinstance(raw, str):
        return {}
    return {k.strip(): v.strip() for k, v in _SPEC_RE.findall(raw)}


def parse_category(raw) -> tuple[str, str]:
    """'["Home >> Kitchen >> Drinkware"]' -> ('Home > Kitchen > Drinkware', 'Drinkware')"""
    if not isinstance(raw, str):
        return "", ""
    s = raw.strip().strip("[]").strip('"')
    parts = [p.strip() for p in s.split(">>") if p.strip()]
    return " > ".join(parts), (parts[-1] if parts else "")


def parse_rating(raw) -> float | None:
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def smart_title(name: str) -> str:
    """Fix ALL CAPS / all lower names but keep things like 'USB-C', '4K'."""
    if name.isupper() or name.islower():
        return " ".join(w if any(c.isdigit() for c in w) else w.capitalize() for w in name.split())
    return name


# ---------- main steps ----------

def load_raw(path: Path | str = config.DATA_CSV) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Turn the messy export into one clean row per product."""
    out = pd.DataFrame()
    out["id"] = df["uniq_id"].str.strip()
    out["name"] = df["product_name"].map(clean_text).map(smart_title)
    cats = df["product_category_tree"].map(parse_category)
    out["category_path"] = cats.map(lambda c: c[0])
    out["category"] = cats.map(lambda c: c[1])
    out["brand"] = df["brand"].map(clean_text)
    out["mrp"] = df["retail_price"].map(parse_price)
    out["price"] = df["discounted_price"].map(parse_price)
    # if the sale price is missing, fall back to MRP
    out["price"] = out["price"].fillna(out["mrp"])
    out["description"] = df["description"].map(clean_text)
    out["specs"] = df["product_specifications"].map(parse_specs)
    out["rating"] = df["product_rating"].map(parse_rating)
    if "type_id" in df.columns:  # ground-truth label, only used for evaluation
        out["type_id"] = df["type_id"]

    # brand missing? the first word of the name is usually the brand
    missing_brand = out["brand"] == ""
    out.loc[missing_brand, "brand"] = out.loc[missing_brand, "name"].str.split().str[0].fillna("")

    out = out[out["name"] != ""]                       # drop rows without a name
    out = out.drop_duplicates(subset=["id"])           # exact duplicate rows
    out = out.drop_duplicates(subset=["name", "price", "description"])  # same product, new id
    return out.reset_index(drop=True)


def row_to_text(row) -> str:
    """The text we embed. Field labels help the embedding model and the LLM."""
    specs = "; ".join(f"{k}: {v}" for k, v in row["specs"].items())
    return (
        f"Product: {row['name']}\n"
        f"Brand: {row['brand']}\n"
        f"Category: {row['category_path']}\n"
        f"Description: {row['description']}\n"
        f"Specs: {specs}"
    )


def to_documents(df: pd.DataFrame) -> list[Document]:
    docs = []
    for _, row in df.iterrows():
        meta = {
            "id": row["id"],
            "name": row["name"],
            "brand": row["brand"],
            "category": row["category"],
            # Chroma metadata can't be None, so use -1 for "unknown"
            "price": float(row["price"]) if pd.notna(row["price"]) else -1.0,
            "rating": float(row["rating"]) if pd.notna(row["rating"]) else -1.0,
        }
        if "type_id" in row:
            meta["type_id"] = row["type_id"]
        docs.append(Document(page_content=row_to_text(row), metadata=meta))
    return docs


def chunk_documents(docs: list[Document]) -> list[Document]:
    """Split long product texts. Most products fit in one chunk; long
    descriptions get split with overlap so no sentence is lost at a border.
    Each chunk keeps its product's metadata, so we can group chunks back
    into products at search time."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=config.CHUNK_SIZE,
        chunk_overlap=config.CHUNK_OVERLAP,
        separators=["\n", ". ", ", ", " ", ""],
    )
    chunks = splitter.split_documents(docs)
    for i, c in enumerate(chunks):
        c.metadata["chunk_id"] = f"{c.metadata['id']}-{i}"
        # keep the product name in every chunk so a lone chunk still makes sense
        if not c.page_content.startswith("Product:"):
            c.page_content = f"Product: {c.metadata['name']}\n{c.page_content}"
    return chunks


def load_products(path: Path | str = config.DATA_CSV) -> tuple[pd.DataFrame, list[Document]]:
    """Convenience: CSV path -> (clean DataFrame, product Documents)."""
    df = clean_dataframe(load_raw(path))
    return df, to_documents(df)
