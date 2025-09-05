
from core.dedupe import find_duplicates

def test_duplicates():
    entries = [
        ("k1","@article{...}", {"metadata":{"doi":"10.1/abc","title":"T","year":"2020"}}),
        ("k2","@article{...}", {"metadata":{"doi":"10.1/abc","title":"T","year":"2020"}}),
        ("k3","@article{...}", {"metadata":{"doi":"10.1/def","title":"T","year":"2020"}}),
    ]
    drops = find_duplicates(entries)
    assert drops == [1]
