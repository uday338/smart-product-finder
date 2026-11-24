from spf.query_parser import parse_query


def test_max_price():
    pq = parse_query("wireless earbuds under ₹2,000")
    assert pq.max_price == 2000 and pq.text == "wireless earbuds"
    assert pq.matches({"price": 1500}) and not pq.matches({"price": 2500})
    assert not pq.matches({"price": -1})       # unknown price is excluded by a max-price filter


def test_k_suffix_and_range_and_rating():
    assert parse_query("laptop stand below 2k").max_price == 2000
    pq = parse_query("headphones between 1000 and 5000 rated 4+")
    assert (pq.min_price, pq.max_price, pq.min_rating) == (1000, 5000, 4)
    assert pq.text == "headphones"
    assert "$and" in pq.where


def test_no_filters():
    pq = parse_query("something to keep coffee hot")
    assert pq.where is None and pq.text == "something to keep coffee hot"
