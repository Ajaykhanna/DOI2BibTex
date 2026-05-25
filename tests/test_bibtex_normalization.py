"""
Test to verify BibTeX value normalization works correctly.
Tests that all field values get wrapped in curly braces.
"""

from core.export import normalize_bibtex_values

def test_normalize_month_without_braces():
    """Test that month=Jan gets converted to month={Jan}"""
    bibtex = """@article{richardson2023,
  title = {A Study},
  author = {Smith},
  month = Jan
}"""
    result = normalize_bibtex_values(bibtex)
    assert 'month = {Jan}' in result, f"Expected 'month = {{Jan}}', got:\n{result}"
    print("✅ Test 1 PASSED: month without braces normalized to {Jan}")

def test_normalize_month_with_braces():
    """Test that month={January} stays as month={January}"""
    bibtex = """@article{smith2020,
  title = {Another Study},
  author = {Jones},
  month = {January}
}"""
    result = normalize_bibtex_values(bibtex)
    assert 'month = {January}' in result, f"Expected 'month = {{January}}', got:\n{result}"
    print("✅ Test 2 PASSED: month with braces stays unchanged")

def test_normalize_volume_number():
    """Test that volume=10 gets converted to volume={10}"""
    bibtex = """@article{test2021,
  title = {Test},
  author = {Author},
  volume = 10,
  number = 5
}"""
    result = normalize_bibtex_values(bibtex)
    assert 'volume = {10}' in result, f"Expected 'volume = {{10}}', got:\n{result}"
    assert 'number = {5}' in result, f"Expected 'number = {{5}}', got:\n{result}"
    print("✅ Test 3 PASSED: numeric fields normalized")

def test_normalize_mixed_formats():
    """Test normalization of entry with mixed braced and unbraced values"""
    bibtex = """@article{mixed2022,
  title = {Mixed Format},
  author = {Author Name},
  year = {2022},
  month = March,
  volume = 15,
  journal = {IEEE Transactions}
}"""
    result = normalize_bibtex_values(bibtex)
    assert 'month = {March}' in result, "month should be normalized"
    assert 'volume = {15}' in result, "volume should be normalized"
    # title and author already have braces
    assert 'title = {Mixed Format}' in result or 'title = { Mixed Format }' in result.replace('\n', ' '), "title format should be preserved"
    print("✅ Test 4 PASSED: mixed formats normalized correctly")

def test_real_world_example():
    """Test the exact output from the user's DOI conversion"""
    bibtex = """@article{richardson2023,
  title = {Machine learning of double-valued nonadiabatic coupling vectors around conical intersections},
  author = {Richardson, Jeremy O.},
  journal = {The Journal of Chemical Physics},
  volume = {158},
  number = {1},
  pages = {011102},
  year = {2023},
  publisher = {AIP Publishing},
  DOI = {10.1063/5.0133191},
  ISSN = {1089-7690},
  url = {http://dx.doi.org/10.1063/5.0133191},
  month = Jan
}"""
    result = normalize_bibtex_values(bibtex)
    assert 'month = {Jan}' in result, f"Expected 'month = {{Jan}}', got:\n{result}"
    print("✅ Test 5 PASSED: real-world example normalized correctly")
    print(f"\nResult excerpt:\n{result[-200:]}")

if __name__ == "__main__":
    print("\n" + "="*70)
    print("TESTING BibTeX VALUE NORMALIZATION")
    print("="*70 + "\n")
    
    try:
        test_normalize_month_without_braces()
        test_normalize_month_with_braces()
        test_normalize_volume_number()
        test_normalize_mixed_formats()
        test_real_world_example()
        
        print("\n" + "="*70)
        print("ALL TESTS PASSED ✅")
        print("="*70)
        print("\nBibTeX values are now normalized to use curly braces!")
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        exit(1)
