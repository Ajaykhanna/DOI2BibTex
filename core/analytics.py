"""Utilities for summarizing metadata entries into simple analytics.

This module provides functions to compute high-level summaries from a list
of bibliographic metadata entries (e.g., year ranges, author/journal counts,
DOI coverage and simple histograms)."""

from __future__ import annotations
from typing import Dict, List, Tuple
from collections import Counter


def summarize(entries: List[Tuple[str, str, dict]]) -> Dict[str, object]:
    """Summarize a list of metadata entries.

    Parameters
    - entries: list of tuples of the form (key, bibtex_str, metadata_dict). The
      metadata_dict typically contains a "metadata" sub-dictionary with fields
      like "year", "author", "journal", and "doi".

    Returns
    A dict with the following keys:
    - total_entries: int, number of provided entries
    - year_range: str, formatted as "YYYY–YYYY" or "N/A" if no valid years
    - unique_authors: int, count of distinct author names parsed
    - unique_journals: int, count of distinct journal names parsed
    - doi_coverage: float, percentage of entries that include a DOI (0-100)
    - top_authors: list, most common authors (name, count)
    - top_journals: list, most common journals (name, count)
    - years_hist: Counter, histogram of publication years

    Notes
    - Years are validated to be in the range 1800–2100 and only the first 4
      digits are considered when parsing.
    - Authors are split on " and " to produce individual names.
    """
    years: List[int] = []
    authors: List[str] = []
    journals: List[str] = []
    doi_count = 0
    for _, _, meta in entries:
        m = meta.get("metadata", {})
        y = m.get("year") or meta.get("year")
        if y and str(y).isdigit():
            yi = int(str(y)[:4])
            if 1800 <= yi <= 2100:
                years.append(yi)
        a = m.get("author") or meta.get("author") or ""
        if a:
            authors.extend([x.strip() for x in a.split(" and ") if x.strip()])
        j = m.get("journal") or meta.get("journal")
        if j:
            journals.append(j)
        if m.get("doi") or meta.get("doi"):
            doi_count += 1
    return {
        "total_entries": len(entries),
        "year_range": f"{min(years)}–{max(years)}" if years else "N/A",
        "unique_authors": len(set(authors)),
        "unique_journals": len(set(journals)),
        "doi_coverage": round(100 * doi_count / max(1, len(entries)), 1),
        "top_authors": Counter(authors).most_common(10),
        "top_journals": Counter(journals).most_common(10),
        "years_hist": Counter(years),
    }
