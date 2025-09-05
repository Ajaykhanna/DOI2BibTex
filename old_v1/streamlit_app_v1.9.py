"""
**Author**: Ajay Khanna
**Date**: Sep.04.2025 (V2)
**Place**: LANL
**Lab**: Dr. Tretiak

### 📧 Contact Information

- **Email**: [akhanna2@ucmerced.edu](mailto:akhanna2@ucmerced.edu) / [quantphobia@gmail.com](mailto:quantphobia@gmail.com)
- **GitHub**: [Ajaykhanna](https://github.com/Ajaykhanna) 🐱‍💻
- **Twitter**: [@samdig](https://twitter.com/samdig) 🐦
- **LinkedIn**: [ajay-khanna](https://www.linkedin.com/in/ajay-khanna) 💼
"""

from __future__ import annotations

import re, time
from typing import Any, Dict, List, Tuple
from collections import Counter

import streamlit as st
from core.http import get_with_retry, polite_headers, get_json_with_retry
from core.doi import clean_doi, is_valid_doi, extract_bibtex_fields
from core.keys import make_key, disambiguate
from core.export import (
    order_bibtex_fields,
    safe_replace_key,
    bibtex_to_ris,
    bibtex_to_endnote,
)
from core.dedupe import find_duplicates
from core.analytics import summarize
from core import cite_styles

import json
import streamlit.components.v1 as components

DOI_BASE = "https://doi.org/"
CROSSREF_JSON = "https://api.crossref.org/works/"
APP_EMAIL = "akhanna2@ucmerced.edu"
DEFAULT_FIELD_ORDER = [
    "title",
    "author",
    "journal",
    "volume",
    "number",
    "pages",
    "year",
    "publisher",
    "doi",
    "abstract",
]

st.set_page_config(page_title="DOI → BibTeX Converter", layout="wide")


def apply_theme(theme: str):
    """
    Apply a visual theme to the Streamlit app by injecting CSS.

    This function constructs CSS tailored for three themes ("light", "gray", "dark")
    and injects it into the Streamlit page via st.markdown(..., unsafe_allow_html=True).

    Parameters
    - theme (str): One of "light", "gray", or "dark". If an unknown value is passed,
      the "light" theme styling will be used as a fallback.

    Side effects
    - Calls st.markdown(...) which modifies the page styling globally.
    - Relies on the HTML/CSS structure used by the Streamlit version in the app; if
      Streamlit internals change the selectors used here may need updating.

    Returns
    - None
    """
    # Bigger tabs with strong specificity; keep inputs readable in dark theme
    base_tab_css = """
    .stTabs [role="tablist"] { gap: 12px; }

    /* Make tabs large and sticky */
    .stTabs [role="tab"] {
        font-size: 1.35rem !important;
        font-weight: 600 !important;
        padding: 14px 24px !important;
        min-height: 50px !important;
        line-height: 1.25 !important;
    }
    /* Ensure inner text respects size */
    .stTabs [role="tab"] p,
    .stTabs [role="tab"] div,
    .stTabs [role="tab"] span { font-size: inherit !important; }

    .stTabs [role="tab"][aria-selected="true"] {
        border-bottom: 4px solid #4CAF50 !important;
    }
    .stTabs [role="tab"] svg {
        width: 1.2em; height: 1.2em; margin-right: 6px; transform: translateY(2px);
    }
    """
    if theme == "dark":
        css = f"""
        <style>
        .stApp {{ background-color: #121212 !important; color: #eaeaea !important; }}
        section[data-testid="stSidebar"] {{ background-color: #181818 !important; }}
        section[data-testid="stSidebar"] * {{ color: #eaeaea !important; }}
        .card {{ background:#1e1e1e; border:1px solid #333; border-radius:10px; padding:1rem; }}

        /* Inputs: force legible colors in dark */
        textarea, input,
        .stTextArea textarea, .stTextInput input, .stNumberInput input,
        [data-baseweb="select"] input, [data-baseweb="select"] div[role="button"],
        .stFileUploader [data-testid="stFileUploadDropzone"] *, .stFileUploader div[role="button"] {{
            background-color: #ffffff !important; color: #111111 !important;
        }}
        ::placeholder {{ color: #777 !important; }}

        {base_tab_css}
        </style>
        """
    elif theme == "gray":
        css = f"""
        <style>
        .stApp {{ background-color: #f2f3f5 !important; color: #111111 !important; }}
        section[data-testid="stSidebar"] {{ background-color: #e9eaed !important; color: #111111 !important; }}
        .card {{ background:#ffffff; border:1px solid #d9dadd; border-radius:10px; padding:1rem; }}
        {base_tab_css}
        </style>
        """
    else:  # light
        css = f"""
        <style>
        .stApp {{ background-color: #ffffff !important; color: #111111 !important; }}
        section[data-testid="stSidebar"] {{ background-color: #fbfbfb !important; color: #111111 !important; }}
        .card {{ background:#ffffff; border:1px solid #e5e5e5; border-radius:10px; padding:1rem; }}
        {base_tab_css}
        </style>
        """
    st.markdown(css, unsafe_allow_html=True)


def render_copy_to_clipboard_button(
    text: str,
    label: str = "Copy cite keys",
    height: int = 40,
    full_width: bool = True,
    offset_top_px: int = -2,
) -> None:
    """
    Render a small HTML/JS button that copies the provided text to the clipboard.

    Behavior
    - The provided `text` is JSON-encoded for safe embedding in the HTML/JS snippet.
    - Uses navigator.clipboard when running in a secure context (recommended).
    - Falls back to creating a hidden textarea + document.execCommand('copy') when
      navigator.clipboard is unavailable.

    Parameters
    - text (str): The exact text that will be copied to the clipboard.
    - label (str): Button label shown to the user (default: "Copy cite keys").
    - height (int): Height used when embedding the HTML via components.html(...).

    Side effects
    - Injects HTML and JavaScript into the Streamlit page via components.html(...).
    - Alters the button label briefly to indicate success/failure.

    Returns
    - None
    """
    js_text = json.dumps(text)  # safe embedding
    width_style = "width:100%;" if full_width else ""
    html = f"""
    <div style="display:block; {width_style}; margin-top:{offset_top_px}px;">
      <button id="copyBtn"
              style="display:block; {width_style}
                     height:{height}px; line-height:{height-2}px;
                     padding:0 12px; border:1px solid #ccc; border-radius:8px;
                     cursor:pointer; background:#f7f7f7; font-size:14px;">
        📋 {label}
      </button>
    </div>
    <script>
      const txt = {js_text};
      const btn = document.getElementById('copyBtn');
      async function doCopy() {{
        try {{
          if (navigator.clipboard && window.isSecureContext) {{
            await navigator.clipboard.writeText(txt);
          }} else {{
            const ta = document.createElement('textarea');
            ta.value = txt; ta.style.position = 'fixed'; ta.style.left = '-9999px';
            document.body.appendChild(ta); ta.focus(); ta.select();
            document.execCommand('copy'); ta.remove();
          }}
          btn.textContent = '✔ Copied';
          setTimeout(() => btn.textContent = '📋 {label}', 1000);
        }} catch (e) {{
          btn.textContent = '❌';
          setTimeout(() => btn.textContent = '📋 {label}', 1000);
        }}
      }}
      btn.addEventListener('click', doCopy);
    </script>
    """
    # +10 for a little vertical breathing room like st.button
    components.html(html, height=height + 10)


def upsert_bibtex_field(bibtex: str, field: str, value: str) -> str:
    """
    Insert or update a named field inside a single BibTeX entry string.

    Intended use
    - If the entry already contains a field with the given name (case-insensitive),
      the function replaces the field's value with `value`.
    - If the field is not present, the function inserts it just before the closing
      brace of the BibTeX entry, preserving a trailing comma where appropriate.

    Parameters
    - bibtex (str): The raw BibTeX entry text to modify.
    - field (str): The BibTeX field name to upsert (e.g., "journal", "abstract").
    - value (str): The value to set for the field. If empty or falsy, the original
      `bibtex` is returned unchanged.

    Returns
    - str: The updated BibTeX entry text.

    Notes
    - Uses regular expressions to find fields; supports multiline and DOTALL patterns.
    - Designed for a single-entry string; behavior on multi-entry text is undefined.
    """
    import re as _re

    if not value:
        return bibtex
    pat = _re.compile(
        rf"(^\s*{_re.escape(field)}\s*=\s*\{{)(.*?)(\}}\s*,?)",
        _re.IGNORECASE | _re.MULTILINE | _re.DOTALL,
    )

    def _repl(m):
        return m.group(1) + value + m.group(3)

    new, n = pat.subn(_repl, bibtex)
    if n > 0:
        return new
    closing = _re.compile(r"\n\}$", _re.MULTILINE)
    return closing.sub(
        lambda m: f",\n  {field} = {{{value}}}\n}}", bibtex.strip(), count=1
    )


if "entries" not in st.session_state:
    st.session_state.entries: List[Tuple[str, str, Dict[str, Any]]] = []
if "analytics" not in st.session_state:
    st.session_state.analytics: Dict[str, Any] = {}
if "prefs" not in st.session_state:
    st.session_state.prefs = {
        "theme": "light",
        "batch_size": 50,
        "field_order": DEFAULT_FIELD_ORDER,
        "key_pattern": "author_year",
        "remove_duplicates": True,
        "validate_dois": True,
        "include_quality": True,
        "normalize_authors": True,
        "include_abstracts": False,
        "fetch_abstracts": False,
        "use_abbrev_journal": False,
        "timeout": 10,
        "max_retries": 3,
        "concurrency": 1,
        "style_preview": "APA",
        "show_progress": False,
    }

with st.sidebar:
    st.header("Settings")
    theme = st.radio(
        "Theme",
        ["light", "gray", "dark"],
        index=["light", "gray", "dark"].index(
            st.session_state.prefs.get("theme", "light")
        ),
    )
    st.session_state.prefs["theme"] = theme
    apply_theme(theme)

    st.subheader("Processing")
    st.session_state.prefs["batch_size"] = st.number_input(
        "Batch size", 1, 500, st.session_state.prefs["batch_size"]
    )
    st.session_state.prefs["show_progress"] = st.toggle(
        "Show progress animation", value=st.session_state.prefs["show_progress"]
    )

    st.subheader("Citation")
    st.session_state.prefs["field_order"] = st.multiselect(
        "BibTeX field order",
        DEFAULT_FIELD_ORDER,
        default=st.session_state.prefs["field_order"],
    )
    st.session_state.prefs["key_pattern"] = st.selectbox(
        "Citation key pattern",
        ["author_year", "first_author_title_year", "journal_year"],
        index=["author_year", "first_author_title_year", "journal_year"].index(
            st.session_state.prefs["key_pattern"]
        ),
    )
    st.session_state.prefs["style_preview"] = st.selectbox(
        "Preview style",
        ["APA", "MLA", "Chicago", "None"],
        index=["APA", "MLA", "Chicago", "None"].index(
            st.session_state.prefs["style_preview"]
        ),
    )

st.markdown(
    '<div style="text-align:center; padding:16px 0;"><h1>🔬 DOI → BibTeX Converter</h1><p>Convert DOIs, export, and analyze.</p></div>',
    unsafe_allow_html=True,
)

tab1, tab2, tab3, tab4 = st.tabs(
    ["🔄 Convert & Results", "⚙️ Advanced", "📈 Analytics", "ℹ️ Help"]
)


def parse_input(raw: str, file) -> List[str]:
    """
    Parse raw input (text area) and optional uploaded file to extract DOIs.

    Processing steps
    - Split the provided raw text and file contents on whitespace and commas.
    - Decode uploaded file contents with errors='ignore' and split similarly.
    - Clean each candidate string using clean_doi().
    - Optionally validate DOIs using is_valid_doi() based on st.session_state prefs.

    Parameters
    - raw (str): Raw text pasted by the user (may contain multiple DOIs).
    - file: Uploaded file-like object (expected to support .read()) or None.

    Returns
    - List[str]: A list of cleaned (and optionally validated) DOI strings ready for
      processing. If validation is enabled, invalid DOIs are filtered out.

    Side effects
    - Reads from `file` if provided (consumes its content).
    - Consults st.session_state.prefs["validate_dois"] to decide whether to validate.
    """
    items: List[str] = []
    if raw:
        parts = re.split(r"[\s,]+", raw.strip())
        items.extend([p for p in parts if p])
    if file is not None:
        text = file.read().decode(errors="ignore")
        parts = re.split(r"[\s,]+", text.strip())
        items.extend([p for p in parts if p])
    cleaned = [clean_doi(x) for x in items]
    if st.session_state.prefs["validate_dois"]:
        cleaned = [x for x in cleaned if is_valid_doi(x)]
    return cleaned


def fetch_bibtex(
    doi: str, timeout: int, max_retries: int
) -> Tuple[str, str, Dict[str, Any]]:
    """
    Fetch a BibTeX entry for a DOI and optionally enrich it using Crossref JSON.

    Workflow
    1. Query DOI resolver (DOI_BASE + doi) to obtain a BibTeX response.
    2. If requested via preferences, query Crossref JSON to fetch abstract and
       container-title information (full title and short/abbreviated title).
    3. Normalize authors if enabled.
    4. Compute a citation key using make_key() and disambiguate() and replace the
       key inside the BibTeX entry if necessary.
    5. Optionally choose abbreviated/full journal names and upsert the journal
       or abstract fields into the BibTeX text.
    6. Re-order fields using order_bibtex_fields() according to preferences.

    Parameters
    - doi (str): DOI string (already cleaned) to fetch.
    - timeout (int): HTTP request timeout in seconds.
    - max_retries (int): Maximum number of retries for HTTP requests.

    Returns
    - Tuple[str, str, Dict[str, Any]]:
      * key (str): The final citation key (or "unknown" on failure).
      * bib (str): The BibTeX entry text (or an error message in the string on failure).
      * meta (dict): Metadata dictionary with at least:
          - "doi": original DOI
          - "status": "processing" | "ok" | "error"
          - "error": optional error message when status == "error"
          - "metadata": parsed BibTeX fields when status == "ok"

    Side effects
    - Reads st.session_state.prefs for runtime options such as fetch_abstracts,
      use_abbrev_journal, normalize_authors, include_abstracts.
    - May perform multiple HTTP requests via get_with_retry and get_json_with_retry.
    """
    meta: Dict[str, Any] = {"doi": doi, "status": "processing"}
    url = DOI_BASE + doi
    resp, err = get_with_retry(
        url, polite_headers(APP_EMAIL), timeout=timeout, max_retries=max_retries
    )
    if err or not resp:
        meta["status"] = "error"
        meta["error"] = err or "request failed"
        return "unknown", f"Error: {doi} → {meta['error']}", meta
    if resp.status_code != 200:
        meta["status"] = "error"
        meta["error"] = f"http {resp.status_code}"
        return "unknown", f"Error: {doi} → http {resp.status_code}", meta
    bib = resp.content.decode("utf-8", errors="replace")
    if "@" not in bib:
        meta["status"] = "error"
        meta["error"] = "no BibTeX in response"
        return "unknown", f"Error: {doi} → no BibTeX", meta

    fields = extract_bibtex_fields(bib)

    need_json = st.session_state.prefs["fetch_abstracts"] or st.session_state.prefs.get(
        "use_abbrev_journal"
    )
    if need_json:
        j, jerr = get_json_with_retry(
            CROSSREF_JSON + doi,
            polite_headers(APP_EMAIL),
            timeout=timeout,
            max_retries=max_retries,
        )
        if not jerr and j and "message" in j:
            msg = j["message"]
            if st.session_state.prefs["fetch_abstracts"]:
                abs_jats = msg.get("abstract")
                if abs_jats:
                    import re as _re

                    fields["abstract"] = _re.sub(r"<[^>]+>", "", abs_jats).strip()
            full = None
            if isinstance(msg.get("container-title"), list) and msg["container-title"]:
                full = msg["container-title"][0]
            elif isinstance(msg.get("container-title"), str):
                full = msg["container-title"]
            short = None
            if (
                isinstance(msg.get("short-container-title"), list)
                and msg["short-container-title"]
            ):
                short = msg["short-container-title"][0]
            elif isinstance(msg.get("short-container-title"), str):
                short = msg["short-container-title"]
            if full:
                fields["journal_full"] = full
            if short:
                fields["journal_abbrev"] = short

    if st.session_state.prefs["normalize_authors"] and "author" in fields:
        fields["author"] = re.sub(r"\s+", " ", fields["author"]).strip()

    base = make_key(fields, st.session_state.prefs["key_pattern"])
    key = disambiguate(base, set())
    old_key = fields.get("key", "")
    if old_key and old_key != key:
        bib = safe_replace_key(bib, old_key, key)
    fields["key"] = key

    if st.session_state.prefs.get("use_abbrev_journal") and fields.get(
        "journal_abbrev"
    ):
        fields["journal"] = fields["journal_abbrev"]
        bib = upsert_bibtex_field(bib, "journal", fields["journal_abbrev"])
    elif fields.get("journal_full"):
        fields.setdefault("journal", fields["journal_full"])
        bib = upsert_bibtex_field(bib, "journal", fields["journal"])

    if not st.session_state.prefs["include_abstracts"] and "abstract" in fields:
        fields.pop("abstract", None)
    if st.session_state.prefs["include_abstracts"] and fields.get("abstract"):
        bib = upsert_bibtex_field(bib, "abstract", fields["abstract"])

    meta["status"] = "ok"
    meta["metadata"] = fields
    bib = order_bibtex_fields(
        bib, st.session_state.prefs["field_order"] or DEFAULT_FIELD_ORDER
    )
    return key, bib, meta


with tab1:
    col1, col2 = st.columns(2)
    with col1:
        raw = st.text_area(
            "Paste DOIs (comma or newline separated)",
            height=180,
            placeholder="10.1038/nphys1170\nhttps://doi.org/10.1145/3292500.3330701",
        )
    with col2:
        up = st.file_uploader("or upload .txt / .csv with DOIs", type=["txt", "csv"])

    if st.button("Convert"):
        dois = parse_input(raw, up)
        if not dois:
            st.warning("No valid DOIs found.")
        else:
            timeout = st.session_state.prefs["timeout"]
            retries = st.session_state.prefs["max_retries"]
            entries: List[Tuple[str, str, Dict[str, Any]]] = []
            prog = st.progress(0.0, text="Processing DOIs…")
            total = max(1, len(dois))
            for i, doi in enumerate(dois, 1):
                key, bib, meta = fetch_bibtex(doi, timeout, retries)
                entries.append((key, bib, meta))
                prog.progress(i / total, text=f"{i}/{total}: {doi}")
                if st.session_state.prefs["show_progress"]:
                    time.sleep(0.1)

            if st.session_state.prefs["remove_duplicates"]:
                drops = find_duplicates(entries)
                if drops:
                    st.info(f"Removed {len(drops)} duplicate(s).")
                    entries = [e for idx, e in enumerate(entries) if idx not in drops]

            st.session_state.entries = entries
            st.session_state.analytics = summarize(entries)
            st.success(
                f"Converted {len(entries)} entries. See the Results and Analytics tabs."
            )

    # --- Results section (inline – aggregated) ---
    st.markdown("### Results")

    if not st.session_state.entries:
        st.info("No results yet — convert some DOIs first.")
    else:
        # --- One box with all cite keys ---
        keys = [k for k, _, _ in st.session_state.entries]
        keys_text = ", ".join(keys)
        edited_keys = st.text_area("Cite Keys", keys_text, height=80, key="keys_box")

        c_apply, c_copy, _ = st.columns([1, 1, 6], gap="small")

        with c_apply:
            if st.button(
                "Apply keys", key="apply_keys_global", use_container_width=True
            ):
                import re as _re

                new_keys = [
                    k.strip() for k in _re.split(r"[,\n]+", edited_keys) if k.strip()
                ]
                if len(new_keys) != len(keys):
                    st.error(
                        f"Expected {len(keys)} keys, got {len(new_keys)}. Keep the same count (comma or newline separated)."
                    )
                else:
                    updated = []
                    for (old_key, bib, meta), new_key in zip(
                        st.session_state.entries, new_keys
                    ):
                        if new_key != old_key:
                            from core.export import safe_replace_key

                            bib = safe_replace_key(bib, old_key, new_key)
                            meta["metadata"]["key"] = new_key
                        updated.append((new_key, bib, meta))
                    st.session_state.entries = updated
                    st.success("Updated all keys.")
                    st.experimental_rerun()

        with c_copy:
            # exact same visual height as st.button + small upward nudge
            render_copy_to_clipboard_button(
                edited_keys,
                label="Copy cite keys",
                height=40,
                offset_top_px=-8,
                full_width=True,
            )
        # --- Downloads: always recomputed from current session state ---
        metas = [e[2].get("metadata", {}) for e in st.session_state.entries]
        from core.export import bibtex_to_ris, bibtex_to_endnote

        all_bib = "\n\n".join([b for _, b, _ in st.session_state.entries])
        ris = "\n\n".join([bibtex_to_ris(m) for m in metas if m])
        enw = "\n\n".join([bibtex_to_endnote(m) for m in metas if m])

        db1, db2, db3 = st.columns(3)
        with db1:
            st.download_button(
                "Download .bib",
                data=all_bib.encode(),
                file_name="references.bib",
                mime="text/plain",
                use_container_width=True,
            )
        with db2:
            st.download_button(
                "Download .ris",
                data=ris.encode(),
                file_name="references.ris",
                mime="text/plain",
                use_container_width=True,
            )
        with db3:
            st.download_button(
                "Download .enw",
                data=enw.encode(),
                file_name="references.enw",
                mime="text/plain",
                use_container_width=True,
            )

        # --- One combined BibTeX block ---
        st.markdown("#### BibTeX Entries")
        st.code(all_bib, language="bibtex")

        # --- One combined style preview (APA/MLA/Chicago) ---
        style = st.session_state.prefs["style_preview"]
        if style != "None":
            from core import cite_styles

            previews = []
            for _, _, meta in st.session_state.entries:
                fields = meta.get("metadata", {})
                if not fields:
                    continue
                if style == "APA":
                    previews.append(cite_styles.format_apa(fields))
                elif style == "MLA":
                    previews.append(cite_styles.format_mla(fields))
                else:
                    previews.append(cite_styles.format_chicago(fields))
            st.markdown("#### Style Preview")
            st.text_area(
                "Preview",
                value="\n\n".join(previews),
                height=220,
                key="style_preview_box",
            )


with tab2:
    st.markdown("### Advanced Settings")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Citation**")
        pattern_help = {
            "author_year": "smith2023",
            "first_author_title_year": "smithanalysis2023",
            "journal_year": "nature2023",
        }
        st.session_state.prefs["key_pattern"] = st.radio(
            "Citation Key Pattern",
            list(pattern_help.keys()),
            index=list(pattern_help.keys()).index(
                st.session_state.prefs["key_pattern"]
            ),
            format_func=lambda x: f"{x.replace('_',' ').title()} ({pattern_help[x]})",
        )
        st.session_state.prefs["field_order"] = st.multiselect(
            "Field order",
            DEFAULT_FIELD_ORDER,
            default=st.session_state.prefs["field_order"],
        )
        st.session_state.prefs["use_abbrev_journal"] = st.checkbox(
            "Use journal abbreviations in exports",
            value=st.session_state.prefs["use_abbrev_journal"],
        )
    with col2:
        st.markdown("**Data processing**")
        st.session_state.prefs["remove_duplicates"] = st.checkbox(
            "Remove duplicate entries",
            value=st.session_state.prefs["remove_duplicates"],
        )
        st.session_state.prefs["validate_dois"] = st.checkbox(
            "Validate DOI formats", value=st.session_state.prefs["validate_dois"]
        )
        st.session_state.prefs["include_quality"] = st.checkbox(
            "Calculate quality scores (summary only)",
            value=st.session_state.prefs["include_quality"],
        )
        st.session_state.prefs["fetch_abstracts"] = st.checkbox(
            "Fetch abstracts (Crossref JSON)",
            value=st.session_state.prefs["fetch_abstracts"],
        )
        st.session_state.prefs["include_abstracts"] = st.checkbox(
            "Include abstracts in exports",
            value=st.session_state.prefs["include_abstracts"],
        )
        st.session_state.prefs["normalize_authors"] = st.checkbox(
            "Normalize author names", value=st.session_state.prefs["normalize_authors"]
        )

    st.markdown("**Performance**")
    c1, c2, c3 = st.columns(3)
    st.session_state.prefs["timeout"] = c1.slider(
        "Timeout (s)", 5, 30, st.session_state.prefs["timeout"]
    )
    st.session_state.prefs["max_retries"] = c2.slider(
        "Max retries", 1, 6, st.session_state.prefs["max_retries"]
    )
    st.session_state.prefs["concurrency"] = c3.slider(
        "Concurrent requests (not used yet)",
        1,
        10,
        st.session_state.prefs["concurrency"],
    )
    st.info("Settings are applied to the next conversion run.")


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


with tab3:
    st.markdown("### Bibliography Analytics")
    if not st.session_state.entries:
        st.info("No data yet — convert some DOIs first.")
    else:
        info = st.session_state.analytics or summarize(st.session_state.entries)
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Total", info["total_entries"])
        c2.metric("Year range", info["year_range"])
        c3.metric("Unique authors", info["unique_authors"])
        c4.metric("Unique journals", info["unique_journals"])
        c5.metric("DOI coverage %", info["doi_coverage"])
        st.markdown("---")
        colA, colB = st.columns(2)
        if info.get("years_hist"):
            years = []
            for y, cnt in info["years_hist"].items():
                years.extend([y] * cnt)
            colA.markdown(create_timeline_chart(years), unsafe_allow_html=True)
        if info.get("top_journals"):
            jdict = {k: v for k, v in info["top_journals"]}
            colB.markdown(
                create_simple_bar_chart(jdict, "Top Journals"), unsafe_allow_html=True
            )
        if info.get("top_authors"):
            adict = {k: v for k, v in info["top_authors"]}
            st.markdown(
                create_simple_bar_chart(adict, "Top Authors"), unsafe_allow_html=True
            )

with tab4:
    st.markdown("### Help & Documentation")
    st.markdown(
        "- Convert single or multiple DOIs; use Advanced to tune citation keys and exports."
    )
    st.markdown(
        "- Use the Analytics tab to visualize publication years, top authors, and journals."
    )
    st.markdown(
        "- If requests are throttled, reduce batch size, increase timeout, or try again later."
    )
    st.markdown("**Contact:** akhanna2@ucmerced.edu")
