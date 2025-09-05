
from core.doi import clean_doi, is_valid_doi

def test_clean_and_validate():
    raw = "https://doi.org/10.1000/xyz123.,)"
    d = clean_doi(raw)
    assert d == "10.1000/xyz123"
    assert is_valid_doi(d)
