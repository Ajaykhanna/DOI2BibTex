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


def create_simple_bar_chart(
    data: Dict[str, int], title: str, max_items: int = 10
) -> str:
    """
    Generate a compact HTML snippet representing a simple horizontal bar chart.

    Behavior
    - Renders up to `max_items` in descending order by value.
    - Produces simple inline styles suitable for embedding via st.markdown(..., unsafe_allow_html=True).
    - If `data` is empty, renders a small card indicating "No data available".

    Parameters
    - data (Dict[str, int]): Mapping of labels to counts/values.
    - title (str): Card title to display above the bars.
    - max_items (int): Maximum number of bars to render (default 10).

    Returns
    - str: HTML string for the bar chart card.
    """
    if not data:
        return f"<div class='card'><h4>{title}</h4><p>No data available</p></div>"
    items = sorted(data.items(), key=lambda x: x[1], reverse=True)[:max_items]
    max_val = max(v for _, v in items) if items else 1
    rows = [f"<div class='card'><h4 style='margin:0 0 8px 0;'>{title}</h4>"]
    for k, v in items:
        w = int((v / max_val) * 220)
        rows.append(
            f"<div style='display:flex; align-items:center; margin:6px 0;'><div style='width:140px; font-size:12px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;'>{k}</div><div style='height:12px; width:{w}px; background:#2196F3; margin:0 8px;'></div><div style='font-size:12px; font-weight:bold;'>{v}</div></div>"
        )
    rows.append("</div>")
    return "\n".join(rows)


def create_timeline_chart(years: List[int]) -> str:
    """
    Create a small publication timeline chart as an HTML snippet.

    Behavior
    - Computes counts per year from the provided years list.
    - Scales bar widths relative to the year with the maximum count.
    - Returns an HTML card that can be rendered with unsafe_allow_html=True.

    Parameters
    - years (List[int]): List of publication years (may contain duplicates).

    Returns
    - str: HTML string visualizing the timeline; if input is empty, returns
      a "No data available" card.

    Notes
    - Expects integer years; non-integer values may produce unexpected output.
    """
    if not years:
        return "<div class='card'><h4>Publication Timeline</h4><p>No data available</p></div>"
    counts = Counter(years)
    keys = sorted(counts.keys())
    max_val = max(counts.values())
    html = ["<div class='card'><h4>Publication Timeline</h4>"]
    for y in keys:
        v = counts[y]
        w = int((v / max_val) * 240)
        html.append(
            f"<div style='display:flex; align-items:center; margin:6px 0;'><div style='width:60px; text-align:right; padding-right:8px;'>{y}</div><div style='height:12px; width:{w}px; background:#4CAF50; margin-right:8px;'></div><div style='font-weight:bold;'>{v}</div></div>"
        )
    html.append("</div>")
    return "\n".join(html)
