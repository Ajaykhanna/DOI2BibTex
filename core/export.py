from __future__ import annotations
import re
from typing import Dict, List


def order_bibtex_fields(bibtex: str, field_order: List[str]) -> str:
    """
    Reorder fields inside a single BibTeX entry using a simple regex-based approach.

    Parameters
    - bibtex: A string containing one BibTeX entry (e.g. "@article{key, title = {..}, ... }").
    - field_order: A list of field names (strings) indicating the desired ordering
      for fields that are present (e.g. ["author", "title", "year"]).

    Returns
    - A new BibTeX entry string with fields ordered: first those present in `field_order`
      (in that order), then the remaining fields in their original sequence.

    Notes
    - This implementation is a naive parser: it expects fields of the form `name = {value}`
      and will not reliably handle nested braces inside values or alternate quoting styles.
    - The function preserves field values but may normalize spacing and braces.
    - Handles special formatting: DOI/ISSN uppercase, month without braces.
    """
    fields = re.findall(r"(\w+)\s*=\s*\{([^}]*)\}", bibtex)
    d = dict(fields)
    entry_type = re.search(r"@(\w+)\{", bibtex)
    key = re.search(r"@\w+\{([^,]+),", bibtex)
    entry_type = entry_type.group(1) if entry_type else "article"
    key = key.group(1) if key else "ref"

    # Build ordered fields list with case-insensitive matching
    field_order_lower = [f.lower() for f in field_order]
    field_map = {k.lower(): k for k, v in fields}  # Map lowercase to original case

    ordered = []
    for target_field in field_order:
        target_lower = target_field.lower()
        # Find the field in the dict (case-insensitive)
        for actual_field, value in fields:
            if actual_field.lower() == target_lower:
                # Use the target field name (which may be DOI, ISSN, etc.)
                ordered.append((target_field, value))
                break

    # Add remaining fields not in field_order
    rest = [(k, v) for k, v in fields if k.lower() not in field_order_lower]
    ordered.extend(rest)

    # Format fields with special handling for month
    formatted_fields = []
    for k, v in ordered:
        if k.lower() == 'month':
            # Month without braces
            formatted_fields.append(f"  {k} = {v}")
        else:
            # Normal field with braces
            formatted_fields.append(f"  {k} = {{{v}}}")

    body = ",\n".join(formatted_fields)
    return f"@{entry_type}{{{key},\n{body}\n}}"


def safe_replace_key(bibtex: str, old: str, new: str) -> str:
    """
    Replace the entry key in a BibTeX header without touching the body.

    Parameters
    - bibtex: Full BibTeX entry text.
    - old: The existing key to replace (exact match).
    - new: The new key to insert.

    Returns
    - The modified BibTeX entry with the header key replaced if a header match is found.

    Behavior notes
    - Only replaces the key that appears in the entry header pattern "@type{KEY,".
    - Uses a single substitution (count=1) and multiline mode to avoid accidental replacements
      elsewhere in the file.
    - The function does not validate uniqueness or BibTeX key syntax beyond the header match.
    """
    # Replace only in the entry header "@type{KEY,"
    return re.sub(
        rf"(^@\w+\{{){re.escape(old)}(,)", rf"\1{new}\2", bibtex, count=1, flags=re.M
    )


def bibtex_to_ris(meta: Dict[str, str]) -> str:
    """
    Convert a metadata dictionary (from a BibTeX entry) into a simple RIS string.

    Parameters
    - meta: Mapping of BibTeX-like field names to values. Common keys include:
      "title", "journal", "year", "volume", "number", "pages", "doi", "publisher",
      "abstract", "author".

    Returns
    - A string formatted as an RIS record (text lines separated by newlines).

    Behavior notes
    - The function uses a naive mapping of BibTeX keys to RIS tags.
    - The "pages" field is split on the first '-' into SP (start page) and EP (end page)
      if a dash is present; otherwise it's emitted as a single SP line.
    - The "author" value is expected to use " and " separators; each author becomes an AU line.
    - This function produces a minimal RIS record and is suitable for simple export tasks.
    """
    # naive mapping with common fields
    lines = ["TY  - JOUR"]
    mapping = {
        "title": "TI  - ",
        "journal": "JO  - ",
        "year": "PY  - ",
        "volume": "VL  - ",
        "number": "IS  - ",
        "pages": "SP  - ",  # we split later if range
        "doi": "DO  - ",
        "publisher": "PB  - ",
        "abstract": "N2  - ",
    }
    for k, prefix in mapping.items():
        v = meta.get(k)
        if v:
            if k == "pages" and "-" in v:
                sp, ep = v.split("-", 1)
                lines.append(f"SP  - {sp.strip()}")
                lines.append(f"EP  - {ep.strip()}")
            else:
                lines.append(prefix + v)
    # authors
    authors = [a.strip() for a in (meta.get("author", "")).split(" and ") if a.strip()]
    for a in authors:
        lines.append("AU  - " + a)
    lines.append("ER  - ")
    return "\n".join(lines)


def bibtex_to_endnote(meta: Dict[str, str]) -> str:
    """
    Convert a metadata dictionary (from a BibTeX entry) into a simple EndNote string.

    Parameters
    - meta: Mapping of BibTeX-like field names to values. Common keys include:
      "title", "journal", "year", "volume", "number", "pages", "doi", "publisher",
      "abstract", "author".

    Returns
    - A string formatted for simple EndNote import (each piece of metadata on its own line
      prefixed by EndNote tags).

    Behavior notes
    - Uses a naive mapping of fields to EndNote tags ("%T", "%J", "%D", etc.).
    - The "author" value is expected to use " and " separators; each author becomes a "%A" line.
    - This output is intended for basic interoperability and may not cover all EndNote features.
    """
    lines = ["%0 Journal Article"]
    mapping = {
        "title": "%T ",
        "journal": "%J ",
        "year": "%D ",
        "volume": "%V ",
        "number": "%N ",
        "pages": "%P ",
        "doi": "%R ",
        "publisher": "%I ",
        "abstract": "%X ",
    }
    for k, prefix in mapping.items():
        v = meta.get(k)
        if v:
            lines.append(prefix + v)
    authors = [a.strip() for a in (meta.get("author", "")).split(" and ") if a.strip()]
    for a in authors:
        lines.append("%A " + a)
    return "\n".join(lines)


# --- Patched: robust field ordering that preserves extras and supports 'abstract' ---
def order_bibtex_fields(bib: str, order: list[str]) -> str:
    """
    Robust reordering of fields in a single BibTeX entry.

    Description
    - Parses a single BibTeX entry and reorders the fields so that fields named in
      `order` (in that sequence) appear first, followed by any remaining fields in
      their original order. Parsing understands brace- and quote-delimited values
      and preserves original key capitalization and value delimiters.

    Parameters
    - bib: A string containing a single BibTeX entry (may contain newlines).
    - order: A list of field names in the desired order (case-insensitive).

    Returns
    - The reassembled BibTeX entry string with fields reordered. If the input does not
      match a single-entry pattern, the original `bib` string is returned unchanged.

    Behavior and edge cases
    - The parser supports values in braces {...} and double quotes "..." and will attempt
      to respect nested braces by tracking depth.
    - Field name matching for the provided `order` is case-insensitive.
    - Original field names and value delimiters are preserved in the output.
    - Trailing commas are normalized so that only the last field does not end with a comma.
    - This function is more resilient than a naive regex but is not a full BibTeX parser.
    """
    import re as _re

    m = _re.match(r"(@\w+\s*\{\s*[^,]+\s*,)(.*)(\})\s*$", bib.strip(), flags=_re.S)
    if not m:
        return bib
    head, body, tail = m.group(1), m.group(2), m.group(3)

    fields = []
    pos = 0
    while pos < len(body):
        km = _re.search(r"\s*([A-Za-z][A-Za-z0-9_-]*)\s*=\s*", body[pos:])
        if not km:
            break
        key = km.group(1)
        pos += km.end()
        if pos < len(body) and body[pos] == "{":
            depth = 0
            start = pos
            while pos < len(body):
                ch = body[pos]
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        pos += 1
                        break
                pos += 1
            value = body[start:pos].strip()
        elif pos < len(body) and body[pos] == '"':
            pos += 1
            start = pos
            while pos < len(body) and body[pos] != '"':
                pos += 1
            value = '"' + body[start:pos] + '"'
            pos += 1
        else:
            start = pos
            while pos < len(body) and body[pos] not in ",\n":
                pos += 1
            value = body[start:pos].strip()
        # consume until next key, dropping a single trailing comma
        comma_consumed = False
        while pos < len(body) and body[pos] in " \t\r\n,":
            if body[pos] == "," and not comma_consumed:
                comma_consumed = True
            pos += 1
        fields.append((key, value))

    key_to_val = {k.lower(): (k, v) for k, v in fields}
    used = set()
    out_lines = []
    order_l = [k.lower() for k in (order or [])]
    for k in order_l:
        if k in key_to_val:
            orig_k, v = key_to_val[k]
            out_lines.append(f"  {orig_k} = {v},")
            used.add(k)
    for k, v in fields:
        kl = k.lower()
        if kl not in used:
            out_lines.append(f"  {k} = {v},")
    if out_lines:
        out_lines[-1] = out_lines[-1].rstrip(",")
    return head + "\n" + "\n".join(out_lines) + "\n" + tail
