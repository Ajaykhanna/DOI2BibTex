from __future__ import annotations
import re
import hashlib
from typing import Dict


def sanitize(s: str) -> str:
    """
    Return a lowercase, alphanumeric-only version of the input string.

    This function:
    - treats None or empty input as an empty string,
    - lowercases the string,
    - removes any character that is not a-z or 0-9.

    Parameters
    ----------
    s : str
        Input string to sanitize (may be None or empty).

    Returns
    -------
    str
        The sanitized string containing only lowercase letters and digits.
        If the input is None or contains no valid characters, an empty string is returned.

    Examples
    --------
    >>> sanitize("Smith, J.")
    "smithj"
    >>> sanitize(None)
    ""
    """
    s = (s or "").lower()
    s = re.sub(r"[^a-z0-9]+", "", s)
    return s


def first_author_lastname(authors_field: str) -> str:
    """
    Extract and sanitize the last name of the first author from an authors field.

    Expected input formats:
    - "Lastname, First and Other, OtherFirst"
    - "First Last and Other Author"
    If the authors_field is empty or None, returns "anon".

    Parameters
    ----------
    authors_field : str
        The authors string typically found in bibliographic metadata.

    Returns
    -------
    str
        The sanitized last name of the first author (only lowercase letters and digits).
        If the input is empty, returns "anon".

    Notes
    -----
    If the first author contains a comma (e.g. "Lastname, First"), the portion before
    the first comma is taken as the last name. Otherwise the last token is assumed to be
    the last name.

    Examples
    --------
    >>> first_author_lastname("Doe, John and Smith, Jane")
    "doe"
    >>> first_author_lastname("John Doe and Jane Smith")
    "doe"
    >>> first_author_lastname("")
    "anon"
    """
    # expects "Lastname, First and Lastname2, First2"
    if not authors_field:
        return "anon"
    first = authors_field.split(" and ")[0]
    # "Lastname, First" -> Lastname
    if "," in first:
        return sanitize(first.split(",")[0])
    return sanitize(first.split()[-1])


def make_key(meta: Dict[str, str], pattern: str = "author_year") -> str:
    """
    Construct a base bibliographic key from metadata according to a chosen pattern.

    Supported pattern values:
    - "author_year": "<firstauthorlast><year>"
    - "first_author_title_year": "<firstauthorlast><sanitized_title_prefix><year>"
    - "journal_year": "<sanitized_journal><year>"
    Any other pattern falls back to "author_year" behavior.

    The function extracts:
    - author: from meta["author"] (first author last name),
    - title: from meta["title"] (sanitized, truncated to 20 chars),
    - journal: from meta["journal"] or meta["journaltitle"] (sanitized, truncated to 20 chars),
    - year: first 4-digit sequence found in meta["year"] if present.

    If the resulting base would be empty, a stable short fallback id is produced using an
    8-character MD5 hash of title+doi and prefixed with "ref".

    Parameters
    ----------
    meta : Dict[str, str]
        Metadata dictionary possibly containing "author", "title", "journal",
        "journaltitle", "year", "doi".
    pattern : str, optional
        Which pattern to use for the key (default "author_year").

    Returns
    -------
    str
        The generated base key (not yet disambiguated). May be a hashed fallback
        starting with "ref" if insufficient metadata is available.

    Examples
    --------
    >>> make_key({"author":"Doe, John", "year":"2020"})
    "doe2020"
    >>> make_key({"title":"A Study", "doi":"10.1000/xyz"}, pattern="first_author_title_year")
    "anonastudy"
    """
    author = first_author_lastname(meta.get("author", ""))
    title = sanitize(meta.get("title", ""))[:20]
    journal = sanitize(meta.get("journal", meta.get("journaltitle", "")))[:20]
    year = re.search(r"(\d{4})", meta.get("year", ""))
    y = year.group(1) if year else ""

    if pattern == "author_year":
        base = f"{author}{y}"
    elif pattern == "first_author_title_year":
        base = f"{author}{title}{y}"
    elif pattern == "journal_year":
        base = f"{journal}{y}"
    else:
        base = f"{author}{y}"

    if not base:
        # stable short hash fallback
        h = hashlib.md5(
            (meta.get("title", "") + meta.get("doi", "")).encode()
        ).hexdigest()[:8]
        base = f"ref{h}"
    return base


def disambiguate(base: str, existing: set[str]) -> str:
    """
    Ensure the provided base key is unique with respect to an existing set of keys.

    If `base` is not present in `existing`, it is returned unchanged. Otherwise the
    function will try to append single letters 'a'..'z' to `base` (base+'a', base+'b', ...)
    to find a free variant. If all single-letter suffixes are taken, a 2-character
    hex digest (MD5 of the base) is appended as a last-resort suffix.

    Parameters
    ----------
    base : str
        The candidate base key to disambiguate.
    existing : set[str]
        A set of keys already in use.

    Returns
    -------
    str
        A unique key not present in `existing`.

    Examples
    --------
    >>> disambiguate("doe2020", {"doe2020"})
    "doe2020a"
    >>> disambiguate("doe2020", {"doe2020", "doe2020a", ..., "doe2020z"})
    "doe2020<2hex>"
    """
    if base not in existing:
        return base
    # append a,b,c... then 2-digit hash if needed
    suffix = ord("a")
    k = f"{base}a"
    while k in existing and suffix <= ord("z"):
        suffix += 1
        k = f"{base}{chr(suffix)}"
    if k in existing:
        h = hashlib.md5(base.encode()).hexdigest()[:2]
        k = f"{base}{h}"
    return k
