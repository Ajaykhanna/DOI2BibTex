from __future__ import annotations
import re
import urllib.parse
from typing import Dict, Any

DOI_HOSTS = (
    "https://doi.org/",
    "http://doi.org/",
    "https://dx.doi.org/",
    "http://dx.doi.org/",
)
DOI_PREFIXES = ("doi:", "DOI:")

DOI_REGEX = re.compile(r"^10\.\d{4,}(?:\.\d+)*\/[\S]+$", re.IGNORECASE)


def clean_doi(raw: str) -> str:
    """
    Normalize and clean a raw DOI string commonly pasted from various sources.

    Behavior:
    - If `raw` is falsy (None or empty), returns an empty string.
    - Strips leading/trailing whitespace.
    - Removes common DOI URL hosts (e.g. "https://doi.org/") in a case-insensitive way.
    - Removes leading "doi:" / "DOI:" prefixes.
    - URL-decodes percent-encoded sequences (via urllib.parse.unquote).
    - Strips trailing punctuation commonly appended in prose (". , ; : )").
    - Returns the cleaned DOI fragment; this function does not validate the DOI format
      (use is_valid_doi for validation).

    Parameters:
    - raw: str - the raw input that may contain a DOI (URL, prefixed, or naked DOI).

    Returns:
    - str: cleaned DOI (possibly empty).

    Examples:
    - " https://doi.org/10.1000/xyz123 " -> "10.1000/xyz123"
    - "DOI:10.1000/xyz123." -> "10.1000/xyz123"
    - "10.1000%2Fxyz123" -> "10.1000/xyz123"
    """
    if not raw:
        return ""
    doi = raw.strip()
    # strip common hosts
    for host in DOI_HOSTS:
        if doi.lower().startswith(host):
            doi = doi[len(host) :]
            break
    # strip "doi:"
    for pref in DOI_PREFIXES:
        if doi.startswith(pref):
            doi = doi[len(pref) :].strip()
    # de-URL-encode and strip trailing punctuation commonly pasted from prose
    doi = urllib.parse.unquote(doi).strip().rstrip(".,;:)")
    return doi


def is_valid_doi(doi: str) -> bool:
    """
    Validate a DOI string against a conservative regular expression.

    Behavior:
    - Returns True if `doi` matches the DOI_REGEX pattern used by this module.
    - Treats None or empty strings as invalid (returns False).

    Notes:
    - The regex checks for the common DOI structure starting with "10." followed
      by at least four digits and a slash with a non-whitespace suffix.
    - This is a syntactic check only; it does not verify existence or resolvability.

    Parameters:
    - doi: str - the DOI string to validate (should typically be passed through clean_doi first).

    Returns:
    - bool: True if the DOI appears valid syntactically, False otherwise.

    Examples:
    - "10.1000/xyz123" -> True
    - "http://doi.org/10.1000/xyz123" -> False (clean first)
    - "" -> False
    """
    return bool(DOI_REGEX.match(doi or ""))


def extract_bibtex_fields(bibtex: str) -> Dict[str, str]:
    """
    Extract common fields from a BibTeX entry string.

    Behavior:
    - Finds simple key = {value} pairs using a regex and returns them in a dict.
    - Additionally extracts the entry type (e.g. "article", "book") as "entry_type"
      and the entry key (the citation key) as "key" when present.
    - All returned dictionary keys are lowercased and values are whitespace-stripped.

    Limitations:
    - This function handles common, simple BibTeX patterns but does not fully parse
      nested braces, quoted values, comments, or multiline complex fields robustly.
    - For complex BibTeX, use a dedicated parser.

    Parameters:
    - bibtex: str - the raw BibTeX entry text.

    Returns:
    - Dict[str, str]: mapping of field names (lowercased) to their string values.
      May include "entry_type" and "key" if those were present in the entry.

    Example:
    - "@article{smith2020, title={A Study}, author={Smith}, year={2020}}"
      -> {"title": "A Study", "author": "Smith", "year": "2020",
          "entry_type": "article", "key": "smith2020"}
    """
    fields = dict(re.findall(r"(\w+)\s*=\s*\{([^}]*)\}", bibtex or ""))
    # entry type and key
    mtype = re.search(r"@(\w+)\{", bibtex or "")
    mkey = re.search(r"@\w+\{([^,]+),", bibtex or "")
    if mtype:
        fields["entry_type"] = mtype.group(1).lower()
    if mkey:
        fields["key"] = mkey.group(1)
    return {k.lower(): v.strip() for k, v in fields.items()}


def normalize_title(s: str) -> str:
    """
    Normalize a title string for loose comparisons.

    Behavior:
    - Converts input to a string if falsy, strips leading/trailing whitespace.
    - Converts to lowercase.
    - Collapses any run of whitespace (spaces, tabs, newlines) to a single space.

    Use:
    - Useful for case-insensitive and whitespace-insensitive title comparison.

    Parameters:
    - s: str - the title to normalize.

    Returns:
    - str: normalized title.

    Examples:
    - "  The Quick   Brown Fox\n" -> "the quick brown fox"
    """
    s = (s or "").strip().lower()
    s = re.sub(r"\s+", " ", s)
    return s
