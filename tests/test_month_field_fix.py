"""
Test for month field formatting fix in extract_bibtex_fields.
This validates that the function correctly extracts month fields
both with and without curly braces.
"""

from core.doi import extract_bibtex_fields

def test_extract_bibtex_fields_month_with_braces():
    """Test extraction when month has curly braces."""
    bibtex = "@article{Smith2020, title={Test}, month={January}, year={2020}}"
    fields = extract_bibtex_fields(bibtex)
    assert 'month' in fields, "month field should be extracted"
    assert fields['month'] == 'January', f"Expected 'January', got '{fields['month']}'"
    print("✅ Test 1 PASSED: month with braces extracted correctly")

def test_extract_bibtex_fields_month_without_braces():
    """Test extraction when month has no curly braces (the bug case)."""
    bibtex = "@article{Jones2021, title={Another}, month=March, year={2021}}"
    fields = extract_bibtex_fields(bibtex)
    assert 'month' in fields, "month field should be extracted even without braces"
    assert fields['month'] == 'March', f"Expected 'March', got '{fields['month']}'"
    print("✅ Test 2 PASSED: month without braces extracted correctly")

def test_extract_bibtex_fields_multiple_formats():
    """Test extraction with mixed field formats."""
    bibtex = """@article{Mixed2022,
        title={Mixed},
        author={Author},
        month=February,
        year={2022},
        journal={Journal},
        volume=10
    }"""
    fields = extract_bibtex_fields(bibtex)
    assert 'month' in fields, "month field should be extracted"
    assert fields['month'] == 'February'
    assert fields['title'] == 'Mixed'
    assert fields['author'] == 'Author'
    print("✅ Test 3 PASSED: mixed format fields extracted correctly")

def test_extract_bibtex_fields_no_month():
    """Test that entries without month field still work."""
    bibtex = "@article{NoMonth2023, title={No Month}, author={Smith}, year={2023}}"
    fields = extract_bibtex_fields(bibtex)
    assert 'month' not in fields, "month field should not exist"
    assert fields['title'] == 'No Month'
    print("✅ Test 4 PASSED: entries without month extracted correctly")

if __name__ == "__main__":
    print("\n" + "="*70)
    print("TESTING MONTH FIELD EXTRACTION FIX")
    print("="*70 + "\n")
    
    try:
        test_extract_bibtex_fields_month_with_braces()
        test_extract_bibtex_fields_month_without_braces()
        test_extract_bibtex_fields_multiple_formats()
        test_extract_bibtex_fields_no_month()
        
        print("\n" + "="*70)
        print("ALL TESTS PASSED ✅")
        print("="*70)
        print("\nThe month field fix is working correctly!")
        print("Month fields are now captured with or without curly braces.")
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        exit(1)
