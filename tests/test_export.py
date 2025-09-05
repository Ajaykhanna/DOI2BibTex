
from core.export import order_bibtex_fields, safe_replace_key

def test_order_and_replace():
    bib = "@article{abc,\n  year = {2020},\n  title = {T},\n  author = {Doe, Jane}\n}"
    ordered = order_bibtex_fields(bib, ["title","author","year"])
    assert ordered.splitlines()[0].startswith("@article{abc")
    replaced = safe_replace_key(ordered, "abc", "smith2020")
    assert "@article{smith2020" in replaced
