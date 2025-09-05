from __future__ import annotations
from typing import Dict, List
import re


def _authors_list(s: str) -> List[str]:
    """Parse an author string into a list of individual author names.

    Parameters
    - s: A string containing one or more author names separated by the literal " and ".
         Typical input examples:
         "Smith, John and Doe, Jane" or "John Smith and Jane Doe".

    Returns
    - A list of author name strings with surrounding whitespace removed.
    - If the input is None or empty, returns an empty list.

    Notes
    - This function performs a simple split on " and " and does not attempt to
      handle more complex conjunctions or name formats beyond trimming whitespace.
    """
    return [a.strip() for a in (s or "").split(" and ") if a.strip()]


def _authors_apa(authors: List[str]) -> str:
    """Format a list of author names according to a compact APA-style string.

    Parameters
    - authors: A list of author name strings. Each name may be either
               "Lastname, First Middlename" or "First Middlename Lastname".

    Returns
    - A single string with authors formatted in APA name style:
      - Single author: "Lastname, F. M."
      - Two authors: "Lastname1, F. & Lastname2, F."
      - Three or more authors: "Lastname1, F., Lastname2, F., & LastnameN, F."
    - If the authors list is empty, returns an empty string.

    Behavior and edge cases
    - Internally uses apa_name to convert an individual name to the abbreviated form.
    - Preserves order from the input list.
    """

    def apa_name(n: str) -> str:
        """Convert a single author name into APA short form.

        Accepts either "Lastname, First Middlename" or "First Middlename Lastname".
        Produces "Lastname, F. M." where each given name is converted to an initial
        followed by a period. Extra whitespace is trimmed.

        Parameters
        - n: single author name string.

        Returns
        - Formatted name string, or an empty string if input is empty.
        """
        # "Lastname, First Middlename" -> "Lastname, F. M."
        if "," in n:
            last, rest = [x.strip() for x in n.split(",", 1)]
        else:
            parts = n.split()
            last, rest = parts[-1], " ".join(parts[:-1])
        initials = " ".join([p[0].upper() + "." for p in rest.split() if p])
        return f"{last}, {initials}".strip().rstrip(",")

    if not authors:
        return ""
    if len(authors) == 1:
        return apa_name(authors[0])
    if len(authors) == 2:
        return f"{apa_name(authors[0])} & {apa_name(authors[1])}"
    return ", ".join(apa_name(a) for a in authors[:-1]) + f", & {apa_name(authors[-1])}"


def _authors_mla(authors: List[str]) -> str:
    """Format a list of authors in a simple MLA-style string.

    Parameters
    - authors: list of author name strings.

    Returns
    - If no authors: empty string.
    - If one author: returns that author's name unchanged.
    - If multiple authors: returns "FirstAuthor, et al." which is a common concise MLA form.

    Notes
    - This is a compact form intended for short citations and does not implement
      full MLA variations (e.g., inverted names for the first author).
    """
    if not authors:
        return ""
    if len(authors) == 1:
        return authors[0]
    return f"{authors[0]}, et al."


def _authors_chicago(authors: List[str]) -> str:
    """Format a list of authors for Chicago-style citations (concise variants).

    Parameters
    - authors: list of author name strings.

    Returns
    - If no authors: empty string.
    - Single author: returns the name unchanged.
    - Two authors: returns "Author1 and Author2".
    - Three or more: returns "Author1, et al." — a concise variation used in many Chicago contexts.

    Notes
    - This function uses a concise representation and does not cover all Chicago Manual of Style permutations.
    """
    if not authors:
        return ""
    if len(authors) == 1:
        return authors[0]
    if len(authors) == 2:
        return f"{authors[0]} and {authors[1]}"
    return authors[0] + ", et al."


def format_apa(meta: Dict[str, str]) -> str:
    """Build a single-line APA-style citation string from metadata.

    Parameters
    - meta: dictionary containing bibliographic metadata. Common keys used:
        - "author": string of authors separated by " and "
        - "year": year (can contain extra text; first 4-digit year is used)
        - "title": article/title string
        - "journal" or "journaltitle": journal name
        - "volume": volume number
        - "number": issue number
        - "pages": page range
        - "doi": digital object identifier (without the URL)

    Returns
    - A formatted string roughly in APA style:
      "Lastname, F. M. (YYYY). Title. Journal, V(N), pp. P. https://doi.org/DOI"
    - If year cannot be found, "n.d." is used.
    - DOI, volume, issue and pages are included only when present.

    Notes
    - This function produces a compact single-line citation intended for quick display,
      not a full typesetting-accurate APA reference.
    """
    A = _authors_apa(_authors_list(meta.get("author", "")))
    Y = re.search(r"(\d{4})", meta.get("year", "") or "")
    Y = Y.group(1) if Y else "n.d."
    T = meta.get("title", "")
    J = meta.get("journal", meta.get("journaltitle", ""))
    V = meta.get("volume", "")
    N = meta.get("number", "")
    P = meta.get("pages", "")
    D = meta.get("doi", "")
    vol_issue = f"{V}({N})" if V and N else V or ""
    pages = f", {P}" if P else ""
    doi = f" https://doi.org/{D}" if D else ""
    return f"{A} ({Y}). {T}. {J}, {vol_issue}{pages}.{doi}".strip()


def format_mla(meta: Dict[str, str]) -> str:
    """Build a simple MLA-style citation string from metadata.

    Parameters
    - meta: dictionary containing bibliographic metadata. Keys used include:
        - "author" (string with " and " separators)
        - "title"
        - "journal" or "journaltitle"
        - "volume", "number", "year", "pages"

    Returns
    - A compact MLA-style single-line citation such as:
      "Lastname, First. "Title." Journal, V, no. N, YYYY, pp. P."
    - Fields that are missing will be omitted from the output.

    Notes
    - This generates a concise representation and is not a full formal MLA bibliography formatter.
    """
    A = _authors_mla(_authors_list(meta.get("author", "")))
    T = meta.get("title", "")
    J = meta.get("journal", meta.get("journaltitle", ""))
    V = meta.get("volume", "")
    N = meta.get("number", "")
    Y = meta.get("year", "")
    P = meta.get("pages", "")
    vol_issue = []
    if V:
        vol_issue.append(V)
    if N:
        vol_issue.append(f"no. {N}")
    vi = ", ".join(vol_issue)
    parts = [A + ".", f'"{T}."', J + ",", vi + ",", Y + ",", P + "."]
    return " ".join([p for p in parts if p and p != ","]).replace(" ,", ",")


def format_chicago(meta: Dict[str, str]) -> str:
    """Build a concise Chicago-style citation string from metadata.

    Parameters
    - meta: dictionary containing bibliographic metadata. Keys used:
        - "author" (string with " and " separators)
        - "title"
        - "journal" or "journaltitle"
        - "volume", "number", "year", "pages"

    Returns
    - A short Chicago-like citation string such as:
      "Author. "Title." Journal V, no. N (YYYY): P."
    - Missing fields are omitted where sensible.

    Notes
    - This is a compact variant for display; it does not attempt to implement
      the many formal Chicago formatting variants (notes vs author-date).
    """
    A = _authors_chicago(_authors_list(meta.get("author", "")))
    T = meta.get("title", "")
    J = meta.get("journal", meta.get("journaltitle", ""))
    V = meta.get("volume", "")
    N = meta.get("number", "")
    Y = meta.get("year", "")
    P = meta.get("pages", "")
    vi = f"{V}, no. {N}" if V and N else (V or "")
    return f'{A}. "{T}." {J} {vi} ({Y}): {P}.'
