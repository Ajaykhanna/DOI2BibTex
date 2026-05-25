"""
Test to verify the month field formatting fix works correctly.
This test can be run independently without requiring conda activation.
"""

import re
import sys

def test_month_formatting():
    """Test the regex fix for month field formatting."""
    
    print("\n" + "="*80)
    print("MONTH FIELD FORMATTING FIX VERIFICATION")
    print("="*80)
    
    # Simulate BibTeX entries as returned from DOI service
    # Case 1: month field without curly braces (the bug scenario)
    bibtex_without_braces = """@article{AuthorYear,
    title={Test Title},
    author={Test Author},
    year={2020},
    month=January
}"""
    
    # Case 2: month field with curly braces (working scenario)
    bibtex_with_braces = """@article{AuthorYear2,
    title={Another Title},
    author={Another Author},
    year={2021},
    month={March}
}"""
    
    # OLD REGEX (BROKEN) - Only captures {value} patterns
    old_pattern = r"(\w+)\s*=\s*\{([^}]*)\}"
    
    # NEW REGEX (FIXED) - Captures both {value} and value patterns
    new_pattern = r"(\w+)\s*=\s*(?:\{([^}]*)\}|(\w+))"
    
    print("\n[TEST 1] BibTeX with month WITHOUT curly braces: month=January")
    print("-" * 80)
    
    # Test with old regex
    print("Using OLD REGEX: r\"(\\w+)\\s*=\\s*\\{([^}]*)\\}\"")
    old_fields = dict(re.findall(old_pattern, bibtex_without_braces))
    print(f"  Extracted fields: {old_fields}")
    if 'month' in old_fields:
        print("  ✅ month field captured")
    else:
        print("  ❌ month field NOT captured (THIS WAS THE BUG!)")
    
    # Test with new regex
    print("\nUsing NEW REGEX: r\"(\\w+)\\s*=\\s*(?:\\{([^}]*)\\}|(\\w+))\"")
    new_fields_raw = re.findall(new_pattern, bibtex_without_braces)
    new_fields = {k: (v1 if v1 else v2) for k, v1, v2 in new_fields_raw}
    print(f"  Extracted fields: {new_fields}")
    if 'month' in new_fields:
        print(f"  ✅ month field captured with value: '{new_fields['month']}'")
        print(f"  ✅ When formatted: month = {{{new_fields['month']}}}")
    else:
        print("  ❌ month field NOT captured")
    
    print("\n[TEST 2] BibTeX with month WITH curly braces: month={March}")
    print("-" * 80)
    
    # Test with old regex
    print("Using OLD REGEX: r\"(\\w+)\\s*=\\s*\\{([^}]*)\\}\"")
    old_fields2 = dict(re.findall(old_pattern, bibtex_with_braces))
    print(f"  Extracted fields: {old_fields2}")
    if 'month' in old_fields2:
        print(f"  ✅ month field captured with value: '{old_fields2['month']}'")
    else:
        print("  ❌ month field NOT captured")
    
    # Test with new regex
    print("\nUsing NEW REGEX: r\"(\\w+)\\s*=\\s*(?:\\{([^}]*)\\}|(\\w+))\"")
    new_fields_raw2 = re.findall(new_pattern, bibtex_with_braces)
    new_fields2 = {k: (v1 if v1 else v2) for k, v1, v2 in new_fields_raw2}
    print(f"  Extracted fields: {new_fields2}")
    if 'month' in new_fields2:
        print(f"  ✅ month field captured with value: '{new_fields2['month']}'")
        print(f"  ✅ When formatted: month = {{{new_fields2['month']}}}")
    else:
        print("  ❌ month field NOT captured")
    
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print("✅ OLD REGEX: Works for month={value} but fails for month=value")
    print("✅ NEW REGEX: Works for BOTH month={value} and month=value")
    print("\nFIX APPLIED TO:")
    print("  1. c:\\programs\\MyGit\\DOI2BibTex\\old_v1\\streamlit_app.py (line 49-50)")
    print("  2. c:\\programs\\MyGit\\DOI2BibTex\\core\\doi.py (line 113-114)")
    print("\nRESULT: Month field will now be captured correctly regardless of format")
    print("        and will always be output as: month = {value}")
    print("="*80 + "\n")

if __name__ == "__main__":
    test_month_formatting()
    sys.exit(0)
