
from core.cite_styles import format_apa, format_mla, format_chicago

META = {
    "author": "Doe, Jane and Roe, Richard",
    "title": "A Study on Things",
    "journal": "Journal of Stuff",
    "year": "2023",
    "volume": "12",
    "number": "3",
    "pages": "10-20",
    "doi": "10.1000/xyz"
}

def test_apa():
    s = format_apa(META)
    assert "Doe, J." in s and "(2023)" in s

def test_mla():
    s = format_mla(META)
    assert "Doe, Jane, et al." in s

def test_chicago():
    s = format_chicago(META)
    assert "Doe, Jane and Roe, Richard" in s or "Doe, Jane, et al." in s
