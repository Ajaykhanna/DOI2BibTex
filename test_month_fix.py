#!/usr/bin/env python
"""Test script to verify month field formatting after the fix."""

import sys
from old_v1.streamlit_app import doi2bib

# Test with a DOI that should have a month field
test_dois = [
    "10.1038/s42254-019-0039-z",  # Nature Reviews
    "10.1021/acs.jctc.8b00842",    # ACS Journal
]

print("=" * 70)
print("TESTING MONTH FIELD FORMATTING IN BibTeX OUTPUT")
print("=" * 70)

for doi in test_dois:
    print(f"\n\nTesting DOI: {doi}")
    print("-" * 70)
    try:
        cite_key, bibtex = doi2bib(doi)
        print(f"Citation Key: {cite_key}\n")
        print("BibTeX Output:")
        print(bibtex)
        
        # Check if month field is present and correctly formatted
        if "month = {" in bibtex:
            print("\n✅ SUCCESS: Month field is properly formatted with curly braces!")
        elif "month =" in bibtex:
            print("\n⚠️ WARNING: Month field exists but may not be properly formatted")
        else:
            print("\nⓘ INFO: No month field found in this entry")
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}")

print("\n" + "=" * 70)
print("Test completed!")
print("=" * 70)
