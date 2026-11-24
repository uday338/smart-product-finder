import pandas as pd

from spf.ingest import (chunk_documents, clean_dataframe, clean_text, load_raw, parse_category,
                        parse_price, parse_specs, smart_title, to_documents)


def test_parse_price_formats():
    assert parse_price("₹1,299") == 1299
    assert parse_price("Rs. 1299") == 1299
    assert parse_price("INR 12,999") == 12999
    assert parse_price("1299.00") == 1299
    assert parse_price("") is None
    assert parse_price(float("nan")) is None


def test_clean_text_strips_html_and_space():
    assert clean_text("<b>Key Features:</b><br>Great   mug<br/>\n\n") == "Key Features: Great mug"
    assert clean_text("Tom &amp; Jerry") == "Tom & Jerry"


def test_parse_specs_and_category():
    blob = '{"product_specification"=>[{"key"=>"Battery", "value"=>"30 hours"}, {"key"=>"ANC", "value"=>"Yes"}]}'
    assert parse_specs(blob) == {"Battery": "30 hours", "ANC": "Yes"}
    assert parse_category('["Home >> Kitchen >> Drinkware"]') == ("Home > Kitchen > Drinkware", "Drinkware")


def test_smart_title():
    assert smart_title("VOLTIX POWER BANK 2.0") == "Voltix Power Bank 2.0"
    assert smart_title("Voltix USB-C Hub") == "Voltix USB-C Hub"


def test_clean_dataframe_removes_junk():
    raw = load_raw()
    df = clean_dataframe(raw)
    assert len(df) < len(raw)                 # duplicates + nameless rows dropped
    assert (df["name"] != "").all()
    assert df["id"].is_unique
    assert df["price"].notna().mean() > 0.95  # almost every price parsed
    assert not df["description"].str.contains("<").any()


def test_documents_and_chunks_keep_metadata():
    df = clean_dataframe(load_raw()).head(5)
    long = df.copy()
    long.loc[0, "description"] = "Very long description sentence. " * 60
    chunks = chunk_documents(to_documents(long))
    assert len(chunks) > 5                    # the long one got split
    for c in chunks:
        assert {"id", "name", "price", "chunk_id"} <= set(c.metadata)
        assert c.page_content.startswith("Product:")
