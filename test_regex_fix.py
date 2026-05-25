#!/usr/bin/env python
"""Direct test of the regex fix without external dependencies."""

import re

# Simulate the old (broken) regex
bibtex_test = """@article{Smith2020,
    title={A Study},
    author={Smith, John},
    year={2020},
    month=January
}"""

bibtex_test2 = """@article{Jones2021,
    title={Another Study},
    author={Jones, Jane},
    year={2021},
    month={March}
}"""

print("=" * 70)
print("TESTING REGEX FIX FOR MONTH FIELD FORMATTING")
print("=" * 70)

# Old regex (BROKEN)
print("\n### OLD REGEX (BROKEN) ###")
print("Pattern: r\"(\\w+)\\s*=\\s*\\{([^}]*)\\}\"")
old_pattern = r"(\w+)\s*=\s*\{([^}]*)\}"
matches_old = re.findall(old_pattern, bibtex_test)
print(f"\nTest 1 (month = January without braces):")
print(f"Matched fields: {matches_old}")
if not any(k == 'month' for k, v in matches_old):
    print("❌ FAIL: month field NOT captured (EXPECTED - this is the bug)")

matches_old2 = re.findall(old_pattern, bibtex_test2)
print(f"\nTest 2 (month = {{March}} with braces):")
print(f"Matched fields: {matches_old2}")
if any(k == 'month' for k, v in matches_old2):
    print("✅ PASS: month field captured")

# New regex (FIXED)
print("\n\n### NEW REGEX (FIXED) ###")
print("Pattern: r\"(\\w+)\\s*=\\s*(?:\\{([^}]*)\\}|(\\w+))\"")
new_pattern = r"(\w+)\s*=\s*(?:\{([^}]*)\}|(\w+))"
matches_new = re.findall(new_pattern, bibtex_test)
print(f"\nTest 1 (month = January without braces):")
print(f"Matched fields (raw): {matches_new}")
fields_dict = {k: (v1 if v1 else v2) for k, v1, v2 in matches_new}
print(f"Fields dict: {fields_dict}")
if 'month' in fields_dict:
    print(f"✅ PASS: month field captured with value: {fields_dict['month']}")

matches_new2 = re.findall(new_pattern, bibtex_test2)
print(f"\nTest 2 (month = {{March}} with braces):")
print(f"Matched fields (raw): {matches_new2}")
fields_dict2 = {k: (v1 if v1 else v2) for k, v1, v2 in matches_new2}
print(f"Fields dict: {fields_dict2}")
if 'month' in fields_dict2:
    print(f"✅ PASS: month field captured with value: {fields_dict2['month']}")

print("\n" + "=" * 70)
print("REGEX FIX VERIFICATION COMPLETE")
print("=" * 70)
