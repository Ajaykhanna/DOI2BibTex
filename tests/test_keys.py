
from core.keys import make_key, disambiguate

def test_key_and_disambiguate():
    meta = {"author":"Doe, Jane and Roe, Richard", "title":"A Study", "year":"2023"}
    k = make_key(meta, "author_year")
    assert k.startswith("doe2023")
    s = {"doe2023"}
    assert disambiguate(k, s) != "doe2023"
