"""
DOI → BibTeX Converter - Streamlit Application (Version 2)

**Author**: Ajay Khanna
**Date**: Sep.05.2025 (V2 - Reimagined)
**Place**: LANL
**Lab**: Dr. Tretiak

This is a refactored version with improved architecture:
- Separated concerns into logical modules
- Added proper error handling and validation
- Type-safe configuration and state management
- Professional code structure

### 📧 Contact Information

- **Email**: [akhanna2@ucmerced.edu](mailto:akhanna2@ucmerced.edu) / [quantphobia@gmail.com](mailto:quantphobia@gmail.com)
- **GitHub**: [Ajaykhanna](https://github.com/Ajaykhanna) 🐱‍💻
- **Twitter**: [@samdig](https://twitter.com/samdig) 🐦
- **LinkedIn**: [ajay-khanna](https://www.linkedin.com/in/ajay-khanna) 💼
"""

from __future__ import annotations

import json
import logging
import re
import time
from typing import List, Dict, Any

import streamlit as st
import streamlit.components.v1 as components

# Import our refactored modules
from core.config import get_config, update_config, DEFAULT_FIELD_ORDER
from core.state import StateManager, get_state
from core.processor import create_processor
from core.exceptions import (
    handle_exception,
    validate_batch_size,
    display_batch_results,
    ConfigurationError,
)
from core.export import bibtex_to_ris, bibtex_to_endnote
from core import cite_styles


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(page_title="DOI → BibTeX Converter", layout="wide")


def apply_theme(theme: str) -> None:
    """Apply visual theme to the Streamlit app."""
    base_tab_css = """
    .stTabs [role="tablist"] { gap: 12px; }
    .stTabs [role="tab"] {
        font-size: 1.35rem !important;
        font-weight: 600 !important;
        padding: 14px 24px !important;
        min-height: 50px !important;
        line-height: 1.25 !important;
    }
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


def render_copy_button(
    text: str,
    label: str = "Copy",
    height: int = 40,
    full_width: bool = True,
    offset_top_px: int = -8,
) -> None:
    """Render a copy-to-clipboard button."""
    js_text = json.dumps(text)
    width_style = "width:100%;" if full_width else ""
    html = f"""
    <div style="display:block; {width_style} margin-top:{offset_top_px}px;">
      <button id="copyBtn"
              style="display:block; {width_style} height:{height}px; line-height:{height-2}px;
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
    components.html(html, height=height + 10)


def render_sidebar() -> None:
    """Render the sidebar with configuration options."""
    config = get_config()

    with st.sidebar:
        st.header("Settings")

        # Theme selection
        new_theme = st.radio(
            "Theme",
            ["light", "gray", "dark"],
            index=["light", "gray", "dark"].index(config.theme),
        )

        if new_theme != config.theme:
            update_config(theme=new_theme)
            st.rerun()

        apply_theme(config.theme)

        # Processing settings
        st.subheader("Processing")

        new_batch_size = st.number_input(
            "Batch size",
            1,
            500,
            config.batch_size,
            help="Number of DOIs to process in one batch. Smaller batches are more reliable.",
        )

        try:
            validate_batch_size(new_batch_size)
            if new_batch_size != config.batch_size:
                update_config(batch_size=new_batch_size)
        except ConfigurationError as e:
            e.display_error()

        new_show_progress = st.toggle(
            "Show progress animation",
            value=config.show_progress,
            help="Add small delays to visualize progress (slower processing)",
        )

        if new_show_progress != config.show_progress:
            update_config(show_progress=new_show_progress)

        # Citation settings
        st.subheader("Citation")

        new_field_order = st.multiselect(
            "BibTeX field order",
            DEFAULT_FIELD_ORDER,
            default=config.field_order,
            help="Order of fields in exported BibTeX entries",
        )

        if new_field_order != config.field_order:
            update_config(field_order=new_field_order)

        pattern_help = {
            "author_year": "smith2023",
            "first_author_title_year": "smithanalysis2023",
            "journal_year": "nature2023",
        }

        new_key_pattern = st.selectbox(
            "Citation key pattern",
            list(pattern_help.keys()),
            index=list(pattern_help.keys()).index(config.key_pattern),
            format_func=lambda x: f"{x.replace('_',' ').title()} ({pattern_help[x]})",
            help="Format for generating citation keys",
        )

        if new_key_pattern != config.key_pattern:
            update_config(key_pattern=new_key_pattern)

        new_style_preview = st.selectbox(
            "Preview style",
            ["APA", "MLA", "Chicago", "None"],
            index=["APA", "MLA", "Chicago", "None"].index(config.style_preview),
            help="Citation style for preview display",
        )

        if new_style_preview != config.style_preview:
            update_config(style_preview=new_style_preview)


@handle_exception
def render_conversion_tab() -> None:
    """Render the main conversion tab."""
    config = get_config()
    state = get_state()

    # Clear file uploader if flagged (before widget is created)
    if st.session_state.get("clear_file_uploader", False):
        if "doi_file_uploader" in st.session_state:
            del st.session_state.doi_file_uploader
        st.session_state.clear_file_uploader = False

    col1, col2 = st.columns(2)

    with col1:
        raw_input = st.text_area(
            "Paste DOIs (comma or newline separated)",
            height=180,
            placeholder="10.1038/nphys1170\nhttps://doi.org/10.1145/3292500.3330701",
            help="Enter one or more DOIs, separated by commas or newlines",
        )

    with col2:
        uploaded_file = st.file_uploader(
            "or upload .txt / .csv with DOIs",
            type=["txt", "csv"],
            help="Upload a text or CSV file containing DOIs",
            key="doi_file_uploader",
        )

    if st.button("Convert", type="primary"):
        processor = create_processor(config)

        try:
            # Parse input
            dois = processor.parse_input(raw_input, uploaded_file)

            if not dois:
                st.warning("No valid DOIs found in input.")
                return

            # Show processing info
            st.info(f"Processing {len(dois)} DOIs...")

            # Create progress tracking
            progress_bar = st.progress(0.0, text="Starting processing...")

            def update_progress(current: int, total: int, doi: str):
                progress = current / total
                progress_bar.progress(
                    progress,
                    text=f"{current}/{total}: {doi[:50]}{'...' if len(doi) > 50 else ''}",
                )

            # Process batch
            result = processor.process_batch(dois, progress_callback=update_progress)

            # Clear progress bar
            progress_bar.empty()

            # Update application state
            state_manager = StateManager()
            state_manager.clear_entries()  # Clear previous results
            new_state = state_manager.add_entries(result.entries)
            state_manager.update_analytics(result.analytics)

            # Flag to clear file uploader on next run (prevents memory errors)
            st.session_state.clear_file_uploader = True

            # Display results
            display_batch_results(
                result.successful_count, result.failed_count, result.failed_dois
            )

            if result.successful_count > 0:
                st.success(
                    f"✅ Successfully converted {result.successful_count} entries. "
                    "Check the Results and Analytics tabs."
                )

        except Exception as e:
            st.error(f"Processing failed: {str(e)}")
            logger.error(f"Conversion error: {e}")

    # Results section
    render_results_section()


def render_results_section() -> None:
    """Render the results section with entries and downloads."""
    state = get_state()

    st.markdown("### Results")

    if not state.has_entries:
        st.info("No results yet — convert some DOIs first.")
        return

    successful_entries = state.successful_entries

    if not successful_entries:
        st.warning("No successful conversions to display.")
        return

    # Citation keys editor
    keys = [entry.key for entry in successful_entries]
    keys_text = ", ".join(keys)

    edited_keys = st.text_area(
        "Citation Keys",
        keys_text,
        height=80,
        help="Edit citation keys (comma or newline separated). Keep the same count.",
    )

    col_apply, col_copy, _ = st.columns([1, 1, 6], gap="small")

    with col_apply:
        if st.button("Apply keys", use_container_width=True):
            new_keys = [
                k.strip() for k in re.split(r"[,\n]+", edited_keys) if k.strip()
            ]

            if len(new_keys) != len(keys):
                st.error(
                    f"Expected {len(keys)} keys, got {len(new_keys)}. "
                    "Keep the same count (comma or newline separated)."
                )
            else:
                # Update keys in state
                key_mapping = {old: new for old, new in zip(keys, new_keys)}
                StateManager.update_entry_keys(key_mapping)
                st.success("Updated all keys.")
                st.rerun()

    with col_copy:
        render_copy_button(edited_keys, "Copy keys", height=40, offset_top_px=-8)

    # Download buttons
    render_download_section(successful_entries)

    # BibTeX display
    st.markdown("#### BibTeX Entries")
    bibtex_content = state.get_bibtex_content()
    st.code(bibtex_content, language="bibtex")

    # Style preview
    render_style_preview(successful_entries)


def render_download_section(entries: list) -> None:
    """Render download buttons for different formats."""
    # Prepare export data
    all_bib = "\n\n".join(entry.content for entry in entries)

    metadata_list = [entry.metadata.get("metadata", {}) for entry in entries]
    ris_content = "\n\n".join(bibtex_to_ris(meta) for meta in metadata_list if meta)
    enw_content = "\n\n".join(bibtex_to_endnote(meta) for meta in metadata_list if meta)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.download_button(
            "📄 Download .bib",
            data=all_bib.encode(),
            file_name="references.bib",
            mime="text/plain",
            use_container_width=True,
        )

    with col2:
        st.download_button(
            "📋 Download .ris",
            data=ris_content.encode(),
            file_name="references.ris",
            mime="text/plain",
            use_container_width=True,
        )

    with col3:
        st.download_button(
            "📝 Download .enw",
            data=enw_content.encode(),
            file_name="references.enw",
            mime="text/plain",
            use_container_width=True,
        )


def render_style_preview(entries: list) -> None:
    """Render citation style preview."""
    config = get_config()

    if config.style_preview == "None":
        return

    st.markdown("#### Style Preview")

    previews = []
    for entry in entries:
        fields = entry.metadata.get("metadata", {})
        if not fields:
            continue

        if config.style_preview == "APA":
            preview = cite_styles.format_apa(fields)
        elif config.style_preview == "MLA":
            preview = cite_styles.format_mla(fields)
        elif config.style_preview == "Chicago":
            preview = cite_styles.format_chicago(fields)
        else:
            continue

        previews.append(preview)

    if previews:
        st.text_area(
            "Preview",
            value="\n\n".join(previews),
            height=220,
            help=f"Citations formatted in {config.style_preview} style",
        )


def render_advanced_tab() -> None:
    """Render advanced settings tab."""
    config = get_config()

    st.markdown("### Advanced Settings")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Citation Settings**")

        # Key pattern (already handled in sidebar, show current)
        st.info(
            f"Current key pattern: **{config.key_pattern.replace('_', ' ').title()}**"
        )

        new_use_abbrev = st.checkbox(
            "Use journal abbreviations in exports",
            value=config.use_abbrev_journal,
            help="Use abbreviated journal names when available from Crossref",
        )

        if new_use_abbrev != config.use_abbrev_journal:
            update_config(use_abbrev_journal=new_use_abbrev)

    with col2:
        st.markdown("**Data Processing**")

        new_remove_duplicates = st.checkbox(
            "Remove duplicate entries",
            value=config.remove_duplicates,
            help="Automatically remove duplicate DOIs/entries from results",
        )

        new_validate_dois = st.checkbox(
            "Validate DOI formats",
            value=config.validate_dois,
            help="Check DOI format before processing (recommended)",
        )

        new_fetch_abstracts = st.checkbox(
            "Fetch abstracts (Crossref JSON)",
            value=config.fetch_abstracts,
            help="Retrieve abstracts from Crossref API (slower processing)",
        )

        new_include_abstracts = st.checkbox(
            "Include abstracts in exports",
            value=config.include_abstracts,
            help="Include abstract field in BibTeX output",
        )

        new_normalize_authors = st.checkbox(
            "Normalize author names",
            value=config.normalize_authors,
            help="Clean up whitespace in author names",
        )

        # Update config if changed
        updates = {}
        if new_remove_duplicates != config.remove_duplicates:
            updates["remove_duplicates"] = new_remove_duplicates
        if new_validate_dois != config.validate_dois:
            updates["validate_dois"] = new_validate_dois
        if new_fetch_abstracts != config.fetch_abstracts:
            updates["fetch_abstracts"] = new_fetch_abstracts
        if new_include_abstracts != config.include_abstracts:
            updates["include_abstracts"] = new_include_abstracts
        if new_normalize_authors != config.normalize_authors:
            updates["normalize_authors"] = new_normalize_authors

        if updates:
            update_config(**updates)

    # Performance settings
    st.markdown("**Performance Settings**")

    col1, col2, col3 = st.columns(3)

    new_timeout = col1.slider(
        "Timeout (seconds)", 5, 60, config.timeout, help="HTTP request timeout"
    )

    new_max_retries = col2.slider(
        "Max retries",
        1,
        10,
        config.max_retries,
        help="Maximum retry attempts for failed requests",
    )

    new_concurrency = col3.slider(
        "Concurrent requests",
        1,
        10,
        config.concurrency,
        help="Future feature - not yet implemented",
    )

    perf_updates = {}
    if new_timeout != config.timeout:
        perf_updates["timeout"] = new_timeout
    if new_max_retries != config.max_retries:
        perf_updates["max_retries"] = new_max_retries
    if new_concurrency != config.concurrency:
        perf_updates["concurrency"] = new_concurrency

    if perf_updates:
        try:
            update_config(**perf_updates)
        except ConfigurationError as e:
            e.display_error()

    st.info("💡 Settings are applied to the next conversion run.")


def render_analytics_tab() -> None:
    """Render analytics and visualization tab."""
    from core.analytics import create_simple_bar_chart, create_timeline_chart
    from collections import Counter

    state = get_state()

    st.markdown("### Bibliography Analytics")

    if not state.has_entries:
        st.info("No data yet — convert some DOIs first.")
        return

    analytics = state.analytics

    if not analytics:
        st.warning("Analytics not available. Try converting some DOIs first.")
        return

    # Metrics row
    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric("Total", analytics.get("total_entries", 0))
    col2.metric("Year Range", analytics.get("year_range", "N/A"))
    col3.metric("Unique Authors", analytics.get("unique_authors", 0))
    col4.metric("Unique Journals", analytics.get("unique_journals", 0))
    col5.metric("DOI Coverage %", f"{analytics.get('doi_coverage', 0):.1f}")

    st.markdown("---")

    # Charts
    col_left, col_right = st.columns(2)

    # Timeline chart
    with col_left:
        if analytics.get("years_hist"):
            years = []
            for year, count in analytics["years_hist"].items():
                years.extend([year] * count)

            if years:
                st.markdown("**Publication Timeline**")
                year_counts = Counter(years)
                sorted_years = sorted(year_counts.keys())

                # Use Streamlit's built-in chart
                import pandas as pd

                df = pd.DataFrame(
                    {
                        "Year": sorted_years,
                        "Publications": [year_counts[y] for y in sorted_years],
                    }
                )
                st.bar_chart(df.set_index("Year"))

    # Top journals chart
    with col_right:
        if analytics.get("top_journals"):
            st.markdown("**Top Journals**")
            journal_data = dict(analytics["top_journals"][:10])  # Top 10

            if journal_data:
                import pandas as pd

                df = pd.DataFrame(
                    {
                        "Journal": list(journal_data.keys()),
                        "Count": list(journal_data.values()),
                    }
                )
                st.bar_chart(df.set_index("Journal"))

    # Top authors
    if analytics.get("top_authors"):
        st.markdown("**Top Authors**")
        author_data = dict(analytics["top_authors"][:15])  # Top 15

        if author_data:
            import pandas as pd

            df = pd.DataFrame(
                {
                    "Author": list(author_data.keys()),
                    "Count": list(author_data.values()),
                }
            )
            st.bar_chart(df.set_index("Author"))


def render_help_tab() -> None:
    """Render help and documentation tab."""
    st.markdown("### Help & Documentation")

    st.markdown(
        """
    #### 🔄 How to Use
    
    1. **Input DOIs**: Paste DOIs in the text area or upload a file containing DOIs
    2. **Configure Settings**: Use the sidebar and Advanced tab to customize processing
    3. **Convert**: Click the Convert button to process your DOIs
    4. **Export**: Download results in BibTeX, RIS, or EndNote formats
    5. **Analyze**: View analytics and charts in the Analytics tab
    
    #### 📝 Supported Input Formats
    
    - Single DOI: `10.1038/nature12373`
    - Multiple DOIs: Separated by commas, spaces, or newlines
    - URLs: `https://doi.org/10.1038/nature12373`
    - Files: Upload .txt or .csv files with DOIs
    
    #### ⚙️ Settings Guide
    
    - **Batch Size**: Number of DOIs processed together (smaller = more reliable)
    - **Citation Keys**: Format for generating unique identifiers
    - **Field Order**: Customize the order of BibTeX fields
    - **Validation**: Check DOI format before processing
    - **Abstracts**: Fetch and include abstracts (slower but more complete)
    
    #### 🚨 Troubleshooting
    
    - **Timeouts**: Reduce batch size or increase timeout
    - **Rate Limiting**: Wait between requests or use smaller batches  
    - **Invalid DOIs**: Enable DOI validation to filter out bad entries
    - **Missing Data**: Some publishers may not provide complete metadata
    
    #### 📊 Export Formats
    
    - **BibTeX (.bib)**: Standard LaTeX bibliography format
    - **RIS (.ris)**: Reference manager import format
    - **EndNote (.enw)**: EndNote library import format
    """
    )

    st.markdown("---")
    st.markdown(
        "**Contact:** [akhanna2@ucmerced.edu](mailto:akhanna2@ucmerced.edu) | "
        "**GitHub:** [Ajaykhanna](https://github.com/Ajaykhanna)"
    )


def main() -> None:
    """Main application entry point."""
    # Header
    st.markdown(
        '<div style="text-align:center; padding:16px 0;">'
        "<h1>🔬 DOI → BibTeX Converter</h1>"
        "<p>Convert DOIs, export references, and analyze your bibliography.</p>"
        "</div>",
        unsafe_allow_html=True,
    )

    # Sidebar
    render_sidebar()

    # Main tabs
    tab1, tab2, tab3, tab4 = st.tabs(
        ["🔄 Convert & Results", "⚙️ Advanced", "📈 Analytics", "ℹ️ Help"]
    )

    with tab1:
        render_conversion_tab()

    with tab2:
        render_advanced_tab()

    with tab3:
        render_analytics_tab()

    with tab4:
        render_help_tab()


if __name__ == "__main__":
    main()
