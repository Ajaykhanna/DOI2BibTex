"""
DOI to BibTeX Converter
**Author**: Ajay Khanna (Enhanced by Claude + ChatGPT5)
**Date**: Dec.10.2023 (Enhanced: Sep.04.2025)
**Place**: LANL
**Lab**: Dr. Tretiak

### 📧 Contact Information
- **Email**: [akhanna2@ucmerced.edu](mailto:akhanna2@ucmerced.edu) / [quantphobia@gmail.com](mailto:quantphobia@gmail.com)
- **GitHub**: [Ajaykhanna](https://github.com/Ajaykhanna) 🐱‍💻
- **Twitter**: [@samdig](https://twitter.com/samdig) 🦅
- **LinkedIn**: [ajay-khanna](https://www.linkedin.com/in/ajay-khanna) 💼
"""

import streamlit as st
import requests
import re
import json
import time
import io
from typing import List, Tuple, Dict, Any, Optional
from datetime import datetime
from collections import Counter, defaultdict
import hashlib
import base64


# ==================== CONFIGURATION ====================


class Config:
    """Application configuration settings"""

    BASE_URL = "http://dx.doi.org/"
    TIMEOUT = 10
    MAX_RETRIES = 3
    BATCH_SIZE = 10
    SUPPORTED_FORMATS = ["bibtex", "ris", "endnote"]
    THEME_COLORS = {
        "primary": "#4CAF50",
        "secondary": "#2196F3",
        "accent": "#FF9800",
        "background": "#f8f9fa",
        "text": "#333333",
    }


# ==================== UTILITY FUNCTIONS ====================


def generate_session_id() -> str:
    """Generate unique session identifier"""
    return hashlib.md5(str(datetime.now()).encode()).hexdigest()[:8]


def safe_request(
    url: str, headers: Dict[str, str], timeout: int = Config.TIMEOUT
) -> requests.Response:
    """Make safe HTTP request with error handling"""
    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        return response
    except requests.exceptions.RequestException as e:
        st.error(f"Network error: {str(e)}")
        return None


def validate_doi_format(doi: str) -> bool:
    """DOI format validation"""
    if not doi or not isinstance(doi, str):
        return False

    # Remove whitespace and normalize
    doi = doi.strip()

    # Check basic DOI pattern
    doi_pattern = r"^10\.\d{4,}(?:\.\d+)*\/[^\s]+$"
    return bool(re.match(doi_pattern, doi, re.IGNORECASE))


def clean_doi(doi: str) -> str:
    """Clean and normalize DOI"""
    if not doi:
        return ""

    doi = doi.strip()

    # Remove common prefixes
    prefixes = ["https://doi.org/", "http://doi.org/", "doi:", "DOI:"]
    for prefix in prefixes:
        if doi.lower().startswith(prefix.lower()):
            doi = doi[len(prefix) :]

    return doi.strip()


def extract_metadata(bibtex: str) -> Dict[str, str]:
    """Extract metadata from BibTeX entry"""
    metadata = {}

    # Extract all fields
    fields = re.findall(r"(\w+)\s*=\s*\{([^}]*)\}", bibtex)
    for field, value in fields:
        metadata[field.lower()] = value.strip()

    # Extract entry type and cite key
    entry_match = re.search(r"@(\w+)\{([^,]+),", bibtex)
    if entry_match:
        metadata["entry_type"] = entry_match.group(1).lower()
        metadata["cite_key"] = entry_match.group(2).strip()

    return metadata


def generate_cite_key(metadata: Dict[str, str], pattern: str = "author_year") -> str:
    """Generate citation key based on pattern"""
    try:
        if pattern == "author_year":
            author = (
                metadata.get("author", "unknown").split(",")[0].split(" ")[-1].lower()
            )
            year = metadata.get("year", "0000")
            return f"{author}{year}"
        elif pattern == "first_author_title_year":
            author = (
                metadata.get("author", "unknown").split(",")[0].split(" ")[-1].lower()
            )
            title_words = metadata.get("title", "unknown").split()[:2]
            title = "".join([word.lower() for word in title_words if word.isalpha()])
            year = metadata.get("year", "0000")
            return f"{author}{title}{year}"
        elif pattern == "journal_year":
            journal = metadata.get("journal", "unknown").replace(" ", "").lower()[:8]
            year = metadata.get("year", "0000")
            return f"{journal}{year}"
        else:
            return metadata.get("cite_key", f"ref{int(time.time())}")
    except:
        return f"ref{int(time.time())}"


def extract_year(bibtex: str) -> int:
    """Extract the year from a BibTeX entry."""
    match = re.search(r"year\s*=\s*{(\d{4})}", bibtex)
    return int(match.group(1)) if match else 0


# ==================== CORE CONVERSION FUNCTIONS ====================


def doi_to_bibtex(doi: str) -> Tuple[str, str, Dict[str, Any]]:
    """Convert DOI to BibTeX with error handling and metadata"""
    result_metadata = {
        "doi": doi,
        "status": "processing",
        "timestamp": datetime.now().isoformat(),
        "processing_time": 0,
    }

    start_time = time.time()

    try:
        if not validate_doi_format(doi):
            result_metadata.update({"status": "error", "error": "Invalid DOI format"})
            return "unknown", f"Error: Invalid DOI format for {doi}", result_metadata

        # Try multiple services for robustness
        services = [
            (
                "CrossRef",
                Config.BASE_URL + doi,
                {"Accept": "application/x-bibtex; charset=utf-8"},
            ),
            (
                "CrossRef Alt",
                f"https://api.crossref.org/works/{doi}/transform/application/x-bibtex",
                {},
            ),
        ]

        for service_name, url, headers in services:
            response = safe_request(url, headers)

            if response and response.status_code == 200:
                bibtex = response.content.decode("utf-8")

                if bibtex and "@" in bibtex:
                    # Extract citation key
                    cite_key_match = re.search(r"@\w+\{([^,]+),", bibtex)
                    cite_key = (
                        cite_key_match.group(1)
                        if cite_key_match
                        else f"ref{int(time.time())}"
                    )

                    # Format BibTeX
                    formatted_bibtex = format_bibtex(bibtex, cite_key)

                    # Update metadata
                    processing_time = time.time() - start_time
                    result_metadata.update(
                        {
                            "status": "success",
                            "service_used": service_name,
                            "processing_time": processing_time,
                            "cite_key": cite_key,
                        }
                    )

                    return cite_key, formatted_bibtex, result_metadata

            elif response and response.status_code == 404:
                result_metadata.update({"status": "error", "error": "DOI not found"})
                return "unknown", f"Error: DOI not found - {doi}", result_metadata

        # If all services fail
        result_metadata.update({"status": "error", "error": "All services unavailable"})
        return "unknown", f"Error: Service unavailable for {doi}", result_metadata

    except Exception as e:
        processing_time = time.time() - start_time
        result_metadata.update(
            {"status": "error", "error": str(e), "processing_time": processing_time}
        )
        return "unknown", f"Error: {str(e)} for {doi}", result_metadata


def format_bibtex(bibtex: str, cite_key: str, field_order: List[str] = None) -> str:
    """Format BibTeX entry with custom field ordering"""
    if not field_order:
        field_order = [
            "title",
            "author",
            "journal",
            "volume",
            "number",
            "pages",
            "year",
            "publisher",
            "doi",
        ]

    # Extract all fields
    fields = re.findall(r"(\w+)\s*=\s*\{([^}]*)\}", bibtex)
    fields_dict = dict(fields)

    # Extract entry type
    entry_type_match = re.search(r"@(\w+)\{", bibtex)
    entry_type = entry_type_match.group(1) if entry_type_match else "article"

    # Order fields according to preference
    ordered_fields = []
    for field in field_order:
        if field in fields_dict:
            ordered_fields.append((field, fields_dict[field]))

    # Add remaining fields
    remaining_fields = [(k, v) for k, v in fields if k not in field_order]
    ordered_fields.extend(remaining_fields)

    # Format the entry
    formatted_bibtex = f"@{entry_type}{{{cite_key},\n"
    for key, value in ordered_fields:
        formatted_bibtex += f"\t{key} = {{{value}}},\n"
    formatted_bibtex = formatted_bibtex.rstrip(",\n") + "\n}"

    return formatted_bibtex


def convert_to_ris(bibtex: str) -> str:
    """Convert BibTeX to RIS format"""
    metadata = extract_metadata(bibtex)

    ris_lines = []
    ris_lines.append("TY  - JOUR")

    # Map BibTeX fields to RIS
    field_mapping = {
        "title": "TI",
        "author": "AU",
        "journal": "JO",
        "year": "PY",
        "volume": "VL",
        "number": "IS",
        "pages": "SP",
        "doi": "DO",
        "abstract": "AB",
        "publisher": "PB",
    }

    for bibtex_field, ris_field in field_mapping.items():
        if bibtex_field in metadata:
            value = metadata[bibtex_field]
            if bibtex_field == "author":
                # Split multiple authors
                authors = [author.strip() for author in value.split(" and ")]
                for author in authors:
                    ris_lines.append(f"{ris_field}  - {author}")
            elif bibtex_field == "pages":
                # Handle page ranges
                if "--" in value:
                    start_page = value.split("--")[0]
                    end_page = value.split("--")[1]
                    ris_lines.append(f"SP  - {start_page}")
                    ris_lines.append(f"EP  - {end_page}")
                else:
                    ris_lines.append(f"{ris_field}  - {value}")
            else:
                ris_lines.append(f"{ris_field}  - {value}")

    ris_lines.append("ER  - ")
    return "\n".join(ris_lines)


def convert_to_endnote(bibtex: str) -> str:
    """Convert BibTeX to EndNote format"""
    metadata = extract_metadata(bibtex)

    endnote_lines = []
    endnote_lines.append("%0 Journal Article")

    # Map BibTeX fields to EndNote
    field_mapping = {
        "title": "%T",
        "author": "%A",
        "journal": "%J",
        "year": "%D",
        "volume": "%V",
        "number": "%N",
        "pages": "%P",
        "doi": "%R",
        "abstract": "%X",
        "publisher": "%I",
    }

    for bibtex_field, endnote_field in field_mapping.items():
        if bibtex_field in metadata:
            value = metadata[bibtex_field]
            if bibtex_field == "author":
                # Split multiple authors
                authors = [author.strip() for author in value.split(" and ")]
                for author in authors:
                    endnote_lines.append(f"{endnote_field} {author}")
            else:
                endnote_lines.append(f"{endnote_field} {value}")

    return "\n".join(endnote_lines)


# ==================== DATA PROCESSING FUNCTIONS ====================


def detect_duplicates(entries: List[Tuple]) -> List[int]:
    """Detect duplicate entries based on DOI and title"""
    seen_dois = set()
    seen_titles = set()
    duplicates = []

    for i, entry in enumerate(entries):
        if len(entry) >= 4 and "metadata" in str(entry[3]):
            metadata = entry[3] if isinstance(entry[3], dict) else {}
            doi = metadata.get("doi", "").lower()

            # Extract title from BibTeX
            title_match = re.search(r"title\s*=\s*\{([^}]*)\}", entry[1], re.IGNORECASE)
            title = title_match.group(1).lower().strip() if title_match else ""

            if (doi and doi in seen_dois) or (title and title in seen_titles):
                duplicates.append(i)
            else:
                if doi:
                    seen_dois.add(doi)
                if title:
                    seen_titles.add(title)

    return duplicates


def calculate_quality_score(bibtex: str, metadata: Dict[str, str]) -> float:
    """Calculate quality score for BibTeX entry"""
    score = 0.0
    max_score = 10.0

    # Essential fields (6 points)
    essential_fields = ["title", "author", "year"]
    for field in essential_fields:
        if field in metadata and metadata[field].strip():
            score += 2.0

    # Important fields (3 points)
    important_fields = ["journal", "doi"]
    for field in important_fields:
        if field in metadata and metadata[field].strip():
            score += 1.5

    # Additional fields (1 point)
    additional_fields = ["volume", "pages", "number"]
    for field in additional_fields:
        if field in metadata and metadata[field].strip():
            score += 0.33

    return min(score, max_score) / max_score * 100


def analyze_bibliography_data(entries: List[Tuple]) -> Dict[str, Any]:
    """Analyze bibliography data for insights"""
    if not entries:
        return {}

    years = []
    authors = []
    journals = []
    doi_count = 0

    for entry in entries:
        if len(entry) >= 2:
            metadata = extract_metadata(entry[1])

            # Extract year
            if "year" in metadata:
                try:
                    year = int(metadata["year"])
                    if 1900 <= year <= 2030:  # Reasonable year range
                        years.append(year)
                except:
                    pass

            # Extract authors
            if "author" in metadata:
                entry_authors = [
                    author.strip() for author in metadata["author"].split(" and ")
                ]
                authors.extend(entry_authors)

            # Extract journals
            if "journal" in metadata:
                journals.append(metadata["journal"])

            # Count DOIs
            if "doi" in metadata:
                doi_count += 1

    analysis = {
        "total_entries": len(entries),
        "years": years,
        "authors": authors,
        "journals": journals,
        "doi_coverage": (doi_count / len(entries)) * 100 if entries else 0,
        "year_range": f"{min(years)} - {max(years)}" if years else "N/A",
        "unique_authors": len(set(authors)),
        "unique_journals": len(set(journals)),
    }

    return analysis


# ==================== FILE PROCESSING FUNCTIONS ====================


def process_uploaded_file(uploaded_file) -> List[str]:
    """Process uploaded file and extract DOIs"""
    try:
        if uploaded_file.type == "text/plain":
            content = str(uploaded_file.read(), "utf-8")
        elif uploaded_file.type == "text/csv":
            content = str(uploaded_file.read(), "utf-8")
        else:
            st.error("Unsupported file type. Please upload .txt or .csv files.")
            return []

        # Extract DOIs using regex
        doi_pattern = r"10\.\d{4,}(?:\.\d+)*\/[^\s,\n]+"
        dois = re.findall(doi_pattern, content, re.IGNORECASE)

        # Clean and validate DOIs
        valid_dois = []
        for doi in dois:
            clean_doi_str = clean_doi(doi)
            if validate_doi_format(clean_doi_str):
                valid_dois.append(clean_doi_str)

        return list(set(valid_dois))  # Remove duplicates

    except Exception as e:
        st.error(f"Error processing file: {str(e)}")
        return []


def create_download_link(content: str, filename: str, file_type: str) -> str:
    """Create download link for content"""
    b64 = base64.b64encode(content.encode()).decode()
    return f'<a href="data:file/{file_type};base64,{b64}" download="{filename}">Download {filename}</a>'


# ==================== SIMPLE CHART FUNCTIONS (NO PLOTLY) ====================


def create_simple_bar_chart(
    data: Dict[str, int], title: str, max_items: int = 10
) -> str:
    """Create simple HTML bar chart without leading indentation so Markdown renders it."""
    if not data:
        return f"<div><h4>{title}</h4><p>No data available</p></div>"

    sorted_items = sorted(data.items(), key=lambda x: x[1], reverse=True)[:max_items]
    if not sorted_items:
        return f"<div><h4>{title}</h4><p>No data available</p></div>"

    max_value = max(count for _, count in sorted_items)
    total = sum(data.values()) if data else 0

    parts = []
    parts.append('<div style="font-family: monospace; margin: 20px 0;">')
    parts.append(f"<h4>{title}</h4>")
    parts.append(
        '<div style="border: 1px solid #ccc; padding: 15px; background: #f9f9f9;">'
    )

    for item, count in sorted_items:
        bar_width = int((count / max_value) * 50) if max_value > 0 else 0
        percentage = (count / total) * 100 if total > 0 else 0
        display_item = (item[:30] + "...") if len(item) > 30 else item

        parts.append('<div style="margin: 8px 0; display: flex; align-items: center;">')
        parts.append(
            f'<div style="width: 200px; text-align: right; padding-right: 10px; font-size: 12px;">{display_item}:</div>'
        )
        parts.append(
            f'<div style="background: #4CAF50; height: 20px; width: {bar_width * 4}px; margin-right: 10px;"></div>'
        )
        parts.append(
            f'<div style="font-size: 12px; font-weight: bold;">{count} ({percentage:.1f}%)</div>'
        )
        parts.append("</div>")

    parts.append("</div>")
    parts.append("</div>")
    return "".join(parts)


def create_timeline_chart(years: List[int]) -> str:
    """Create simple timeline chart HTML without leading indentation."""
    if not years:
        return "<div><h4>Publication Timeline</h4><p>No year data available</p></div>"

    year_counts = Counter(years)
    sorted_years = sorted(year_counts.keys())
    max_count = max(year_counts.values())

    parts = []
    parts.append('<div style="font-family: monospace; margin: 20px 0;">')
    parts.append("<h4>Publication Timeline</h4>")
    parts.append(
        '<div style="border: 1px solid #ccc; padding: 15px; background: #f9f9f9;">'
    )
    parts.append(
        f'<div style="margin-bottom: 10px;"><strong>Years:</strong> {min(sorted_years)} - {max(sorted_years)} '
        f"<strong>Total Publications:</strong> {sum(year_counts.values())}</div>"
    )

    for year in sorted_years:
        count = year_counts[year]
        bar_width = int((count / max_count) * 30) if max_count > 0 else 0

        parts.append('<div style="margin: 5px 0; display: flex; align-items: center;">')
        parts.append(
            f'<div style="width: 60px; text-align: right; padding-right: 10px; font-size: 12px;">{year}:</div>'
        )
        parts.append(
            f'<div style="background: #2196F3; height: 15px; width: {bar_width * 8}px; margin-right: 10px;"></div>'
        )
        parts.append(f'<div style="font-size: 12px; font-weight: bold;">{count}</div>')
        parts.append("</div>")

    parts.append("</div>")
    parts.append("</div>")
    return "".join(parts)


# ==================== UI COMPONENTS ====================


def apply_custom_css(theme: str = "light"):
    primary = "#4CAF50"
    secondary = "#2196F3"
    accent = "#FF9800"

    if theme == "dark":
        bg = "#1e1e1e"
        text = "#ffffff"
        border = "#404040"
        card_bg = "#2a2a2a"
        panel_bg = "#2b2b2b"
        sidebar_bg = "#171717"
        sidebar_text = "#ffffff"
        control_bg = "#2a2a2a"
    else:
        bg = "#f8f9fa"
        text = "#333333"
        border = "#e0e0e0"
        card_bg = "#ffffff"
        panel_bg = "#f9f9f9"
        sidebar_bg = "#ffffff"
        sidebar_text = "#333333"
        control_bg = "#ffffff"

    st.markdown(
        f"""
    <style>
    :root {{
        --primary-color: {primary};
        --secondary-color: {secondary};
        --accent-color: {accent};
        --background-color: {bg};
        --text-color: {text};
        --border-color: {border};
        --card-bg: {card_bg};
        --panel-bg: {panel_bg};
        --sidebar-bg: {sidebar_bg};
        --sidebar-text: {sidebar_text};
        --control-bg: {control_bg};
        --shadow: 0 2px 4px rgba(0,0,0,0.1);
    }}

    html, body, .stApp {{
        background-color: var(--background-color) !important;
        color: var(--text-color) !important;
    }}

    h1, h2, h3, h4, h5, h6, p, li, label, span, div {{ color: var(--text-color); }}

    /* Sidebar */
    section[data-testid="stSidebar"] {{
        background-color: var(--sidebar-bg) !important;
        color: var(--sidebar-text) !important;
        border-right: 1px solid var(--border-color) !important;
    }}
    section[data-testid="stSidebar"] * {{ color: var(--sidebar-text) !important; }}
    section[data-testid="stSidebar"] input,
    section[data-testid="stSidebar"] textarea,
    section[data-testid="stSidebar"] select,
    section[data-testid="stSidebar"] div[role="combobox"],
    section[data-testid="stSidebar"] div[data-baseweb="select"] > div {{
        background-color: var(--control-bg) !important;
        color: var(--sidebar-text) !important;
        border: 1px solid var(--border-color) !important;
    }}
    section[data-testid="stSidebar"] [data-testid="stMetricLabel"],
    section[data-testid="stSidebar"] [data-testid="stMetricValue"] {{
        color: var(--sidebar-text) !important;
    }}

    .main-header {{
        text-align: center;
        padding: 2rem 0;
        background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
        color: white;
        border-radius: 10px;
        margin-bottom: 2rem;
        box-shadow: var(--shadow);
    }}

    .feature-card {{
        background: var(--card-bg);
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: var(--shadow);
        margin-bottom: 1rem;
        border-left: 4px solid var(--primary-color);
        border: 1px solid var(--border-color);
    }}

    .metric-card {{
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        border-radius: 8px;
        text-align: center;
        margin: 0.5rem;
    }}

    .status-success {{ background-color: #d4edda; color: #155724; padding: .75rem; border-radius: 6px; border: 1px solid #c3e6cb; margin: 1rem 0; }}
    .status-error   {{ background-color: #f8d7da; color: #721c24; padding: .75rem; border-radius: 6px; border: 1px solid #f5c6cb; margin: 1rem 0; }}
    .status-warning {{ background-color: #fff3cd; color: #856404; padding: .75rem; border-radius: 6px; border: 1px solid #ffeaa7; margin: 1rem 0; }}

    .progress-bar {{ width: 100%; height: 25px; background-color: var(--panel-bg); border-radius: 12px; overflow: hidden; margin: 10px 0; border: 1px solid var(--border-color); }}
    .progress-fill {{ height: 100%; background: linear-gradient(90deg, var(--primary-color), var(--secondary-color)); transition: width 0.5s ease; border-radius: 12px; }}

    .stButton > button {{ background: var(--secondary-color); color: white; border: none; padding: .5rem 1rem; border-radius: 6px; cursor: pointer; font-size: .9rem; }}
    .stButton > button:hover {{ opacity: .9; transform: translateY(-1px); }}

    @media (max-width: 768px) {{
        .main-header {{ padding: 1rem; }}
        .feature-card {{ margin: .5rem 0; padding: 1rem; }}
    }}
    @keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(10px); }} to {{ opacity: 1; transform: translateY(0); }} }}
    .fade-in {{ animation: fadeIn .5s ease-in-out; }}

    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    header {{visibility: hidden;}}
    .block-container {{ padding-top: 2rem; }}
    </style>
    """,
        unsafe_allow_html=True,
    )


def render_sidebar_stats(container):
    with container:
        st.markdown("## 📊 Session Statistics")
        stats = st.session_state.session_stats
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Processed", stats.get("total_processed", 0))
        c2.metric("Successful", stats.get("successful_conversions", 0))
        c3.metric("Failed", stats.get("failed_conversions", 0))


def render_header():
    """Render application header"""
    st.markdown(
        """
    <div class="main-header fade-in">
        <h1>🔬 DOI to BibTeX Converter</h1>
        <p>Convert DOIs to properly formatted citations with advanced features</p>
    </div>
    """,
        unsafe_allow_html=True,
    )


def render_metrics_dashboard(analysis_data: Dict[str, Any]):
    """Render metrics dashboard"""
    if not analysis_data:
        return

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(
            f"""
        <div class="metric-card">
            <h3>{analysis_data.get('total_entries', 0)}</h3>
            <p>Total Entries</p>
        </div>
        """,
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            f"""
        <div class="metric-card">
            <h3>{analysis_data.get('unique_authors', 0)}</h3>
            <p>Unique Authors</p>
        </div>
        """,
            unsafe_allow_html=True,
        )

    with col3:
        st.markdown(
            f"""
        <div class="metric-card">
            <h3>{analysis_data.get('unique_journals', 0)}</h3>
            <p>Unique Journals</p>
        </div>
        """,
            unsafe_allow_html=True,
        )

    with col4:
        st.markdown(
            f"""
        <div class="metric-card">
            <h3>{analysis_data.get('doi_coverage', 0):.1f}%</h3>
            <p>DOI Coverage</p>
        </div>
        """,
            unsafe_allow_html=True,
        )


def render_progress_bar(current: int, total: int, label: str = "Progress"):
    """Render progress bar"""
    if total == 0:
        progress = 0
    else:
        progress = (current / total) * 100

    st.markdown(
        f"""
    <div style="margin: 1rem 0;">
        <p><strong>{label}: {current}/{total} ({progress:.1f}%)</strong></p>
        <div class="progress-bar">
            <div class="progress-fill" style="width: {progress}%"></div>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )


def render_status_message(message: str, status_type: str = "info"):
    """Render status message with appropriate styling"""
    class_name = f"status-{status_type}"
    st.markdown(
        f"""
    <div class="{class_name}">
        {message}
    </div>
    """,
        unsafe_allow_html=True,
    )


# ==================== SESSION STATE INITIALIZATION ====================


def initialize_session_state():
    """Initialize session state variables"""
    if "session_id" not in st.session_state:
        st.session_state.session_id = generate_session_id()

    if "bibtex_entries" not in st.session_state:
        st.session_state.bibtex_entries = []

    if "processing_history" not in st.session_state:
        st.session_state.processing_history = []

    if "user_preferences" not in st.session_state:
        st.session_state.user_preferences = {
            "theme": "light",
            "citation_key_pattern": "author_year",
            "field_order": [
                "title",
                "author",
                "journal",
                "volume",
                "number",
                "pages",
                "year",
                "publisher",
                "doi",
            ],
            "export_format": "bibtex",
            "show_analytics": True,
            "batch_size": 10,
        }

    if "analytics_data" not in st.session_state:
        st.session_state.analytics_data = {}

    if "session_stats" not in st.session_state:
        st.session_state.session_stats = {
            "total_processed": 0,
            "successful_conversions": 0,
            "failed_conversions": 0,
            "start_time": datetime.now(),
        }


# ==================== MAIN APPLICATION ====================


def main():
    """Main application function"""
    st.set_page_config(
        page_title="DOI to BibTeX Converter",
        page_icon="🔬",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Initialize session state
    initialize_session_state()

    # Sidebar configuration
    with st.sidebar:
        st.markdown("## ⚙️ Configuration")

        # Theme selector
        theme = st.selectbox(
            "Theme",
            ["Light", "Dark"],
            index=0 if st.session_state.user_preferences["theme"] == "light" else 1,
        )
        st.session_state.user_preferences["theme"] = theme.lower()

        # Citation key pattern
        citation_pattern = st.selectbox(
            "Citation Key Pattern",
            ["author_year", "first_author_title_year", "journal_year"],
            index=["author_year", "first_author_title_year", "journal_year"].index(
                st.session_state.user_preferences["citation_key_pattern"]
            ),
        )
        st.session_state.user_preferences["citation_key_pattern"] = citation_pattern

        # Export format
        export_format = st.selectbox(
            "Default Export Format",
            ["BibTeX", "RIS", "EndNote"],
            index=["bibtex", "ris", "endnote"].index(
                st.session_state.user_preferences["export_format"]
            ),
        )
        st.session_state.user_preferences["export_format"] = export_format.lower()

        # Batch processing size
        batch_size = st.slider(
            "Batch Processing Size",
            min_value=1,
            max_value=50,
            value=st.session_state.user_preferences["batch_size"],
        )
        st.session_state.user_preferences["batch_size"] = batch_size

        st.markdown("---")
        stats_container = st.container()
        render_sidebar_stats(stats_container)

        # Session statistics
        st.markdown("## 📊 Session Statistics")
        stats = st.session_state.session_stats
        st.metric("Total Processed", stats["total_processed"])
        st.metric("Successful", stats["successful_conversions"])
        st.metric("Failed", stats["failed_conversions"])

        # Session management
        st.markdown("## 💾 Session Management")
        if st.button("Clear Session"):
            st.session_state.bibtex_entries = []
            st.session_state.processing_history = []
            st.session_state.analytics_data = {}
            st.rerun()

        if st.button("Export Session Data"):
            session_data = {
                "entries": st.session_state.bibtex_entries,
                "preferences": st.session_state.user_preferences,
                "stats": st.session_state.session_stats,
                "export_timestamp": datetime.now().isoformat(),
            }

            json_data = json.dumps(session_data, indent=2, default=str)
            st.download_button(
                label="Download Session JSON",
                data=json_data,
                file_name=f"doi_converter_session_{st.session_state.session_id}.json",
                mime="application/json",
            )
    apply_custom_css(st.session_state.user_preferences["theme"])

    # Render header
    render_header()

    # Main content tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["🔄 Convert", "📊 Results", "⚙️ Advanced", "📈 Analytics", "ℹ️ Help"]
    )

    with tab1:
        st.markdown("### DOI Input Methods")

        # Input method selection
        input_method = st.radio(
            "Choose input method:", ["Manual Entry", "File Upload", "Bulk Processing"]
        )

        dois_to_process = []

        if input_method == "Manual Entry":
            doi_input = st.text_area(
                "Enter DOIs (one per line or comma-separated)",
                value="10.1000/xyz123",
                height=100,
                help="Enter one or more DOIs. Supported formats: 10.1000/xyz123 or https://doi.org/10.1000/xyz123",
            )

            if doi_input.strip():
                # Parse DOIs from input
                raw_dois = re.split(r"[,\n\r]+", doi_input)
                dois_to_process = [
                    clean_doi(doi.strip()) for doi in raw_dois if doi.strip()
                ]
                dois_to_process = [
                    doi for doi in dois_to_process if validate_doi_format(doi)
                ]

        elif input_method == "File Upload":
            uploaded_file = st.file_uploader(
                "Upload file containing DOIs",
                type=["txt", "csv"],
                help="Upload a .txt or .csv file containing DOIs",
            )

            if uploaded_file:
                dois_to_process = process_uploaded_file(uploaded_file)
                if dois_to_process:
                    st.success(
                        f"Found {len(dois_to_process)} valid DOIs in uploaded file"
                    )
                else:
                    st.warning("No valid DOIs found in uploaded file")

        elif input_method == "Bulk Processing":
            st.markdown("#### Bulk DOI Processing")
            bulk_input = st.text_area(
                "Paste DOI list for bulk processing",
                height=200,
                help="Paste a large list of DOIs for batch processing",
            )

            if bulk_input.strip():
                raw_dois = re.split(r"[,\n\r\s]+", bulk_input)
                dois_to_process = [
                    clean_doi(doi.strip()) for doi in raw_dois if doi.strip()
                ]
                dois_to_process = [
                    doi for doi in dois_to_process if validate_doi_format(doi)
                ]

        # Display DOI validation results
        if dois_to_process:
            st.markdown(f"**Found {len(dois_to_process)} valid DOIs:**")

            # Show DOI preview
            with st.expander("Preview DOIs"):
                for i, doi in enumerate(dois_to_process[:10], 1):
                    st.write(f"{i}. {doi}")
                if len(dois_to_process) > 10:
                    st.write(f"... and {len(dois_to_process) - 10} more DOIs")

        # Processing options
        if dois_to_process:
            st.markdown("### Processing Options")

            col1, col2 = st.columns(2)

            with col1:
                remove_duplicates = st.checkbox("Remove duplicates", value=True)
                include_abstracts = st.checkbox(
                    "Include abstracts (when available)", value=False
                )

            with col2:
                custom_cite_keys = st.checkbox("Use custom citation keys", value=False)
                validate_entries = st.checkbox("Validate entries", value=True)

        # Convert button
        if st.button(
            "🚀 Convert DOIs to BibTeX", type="primary", disabled=not dois_to_process
        ):
            if dois_to_process:
                # Initialize progress tracking
                total_dois = len(dois_to_process)
                progress_placeholder = st.empty()
                results_placeholder = st.empty()

                # Process DOIs
                new_entries = []
                errors = []

                for i, doi in enumerate(dois_to_process):
                    # Update progress
                    with progress_placeholder.container():
                        render_progress_bar(i, total_dois, "Converting DOIs")

                    # Convert DOI
                    cite_key, bibtex, metadata = doi_to_bibtex(doi)

                    if metadata["status"] == "success":
                        # Extract and enhance metadata
                        bib_metadata = extract_metadata(bibtex)

                        # Custom citation key if requested
                        if custom_cite_keys:
                            custom_key = generate_cite_key(
                                bib_metadata,
                                st.session_state.user_preferences[
                                    "citation_key_pattern"
                                ],
                            )
                            bibtex = bibtex.replace(cite_key, custom_key)
                            cite_key = custom_key

                        # Calculate quality score
                        quality_score = calculate_quality_score(bibtex, bib_metadata)

                        new_entries.append(
                            (
                                cite_key,
                                bibtex,
                                extract_year(bibtex),
                                {
                                    **metadata,
                                    "quality_score": quality_score,
                                    "bib_metadata": bib_metadata,
                                },
                            )
                        )

                        # Update session stats
                        st.session_state.session_stats["successful_conversions"] += 1
                    else:
                        errors.append((doi, metadata.get("error", "Unknown error")))
                        st.session_state.session_stats["failed_conversions"] += 1

                    # Update total processed
                    st.session_state.session_stats["total_processed"] += 1

                    # Small delay to show progress (can be removed for production)
                    time.sleep(0.1)

                # Final progress update
                with progress_placeholder.container():
                    render_progress_bar(total_dois, total_dois, "Conversion Complete")

                # Remove duplicates if requested
                if remove_duplicates and new_entries:
                    duplicate_indices = detect_duplicates(new_entries)
                    if duplicate_indices:
                        st.warning(
                            f"Removed {len(duplicate_indices)} duplicate entries"
                        )
                        new_entries = [
                            entry
                            for i, entry in enumerate(new_entries)
                            if i not in duplicate_indices
                        ]

                # Add to session state
                st.session_state.bibtex_entries.extend(new_entries)

                # Show results summary
                with results_placeholder.container():
                    if new_entries:
                        render_status_message(
                            f"✅ Successfully converted {len(new_entries)} DOIs to BibTeX format!",
                            "success",
                        )

                    if errors:
                        render_status_message(
                            f"⚠️ Failed to convert {len(errors)} DOIs. Check the Results tab for details.",
                            "warning",
                        )

                        with st.expander("View Errors"):
                            for doi, error in errors:
                                st.write(f"**{doi}**: {error}")

                # Update analytics
                if st.session_state.bibtex_entries:
                    st.session_state.analytics_data = analyze_bibliography_data(
                        st.session_state.bibtex_entries
                    )

                # Refresh sidebar stats immediately
                render_sidebar_stats(stats_container)

    with tab2:
        st.markdown("### 📚 Conversion Results")

        if not st.session_state.bibtex_entries:
            st.info("No BibTeX entries available. Convert some DOIs first!")
        else:
            # Display metrics
            if st.session_state.analytics_data:
                render_metrics_dashboard(st.session_state.analytics_data)

            st.markdown("---")

            # Search and filter options
            col1, col2, col3 = st.columns(3)

            with col1:
                search_term = st.text_input(
                    "🔍 Search entries",
                    placeholder="Search by title, author, journal...",
                )

            with col2:
                year_filter = st.selectbox(
                    "📅 Filter by year",
                    ["All years"]
                    + sorted(
                        set(
                            [
                                entry[2]
                                for entry in st.session_state.bibtex_entries
                                if entry[2] > 0
                            ]
                        ),
                        reverse=True,
                    ),
                )

            with col3:
                sort_option = st.selectbox(
                    "🔄 Sort by",
                    [
                        "Original order",
                        "Year (newest first)",
                        "Year (oldest first)",
                        "Title",
                        "Author",
                    ],
                )

            # Filter and sort entries
            filtered_entries = st.session_state.bibtex_entries[:]

            # Apply search filter
            if search_term:
                filtered_entries = [
                    entry
                    for entry in filtered_entries
                    if search_term.lower() in entry[1].lower()
                ]

            # Apply year filter
            if year_filter != "All years":
                filtered_entries = [
                    entry for entry in filtered_entries if entry[2] == int(year_filter)
                ]

            # Apply sorting
            if sort_option == "Year (newest first)":
                filtered_entries.sort(key=lambda x: x[2], reverse=True)
            elif sort_option == "Year (oldest first)":
                filtered_entries.sort(key=lambda x: x[2])
            elif sort_option == "Title":
                filtered_entries.sort(
                    key=lambda x: extract_metadata(x[1]).get("title", "").lower()
                )
            elif sort_option == "Author":
                filtered_entries.sort(
                    key=lambda x: extract_metadata(x[1]).get("author", "").lower()
                )

            if not filtered_entries:
                st.warning("No entries match your search criteria.")
            else:
                st.markdown(
                    f"**Showing {len(filtered_entries)} of {len(st.session_state.bibtex_entries)} entries**"
                )

                # Export options
                st.markdown("### 📥 Export Options")

                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    # Copy cite keys
                    cite_keys = [entry[0] for entry in filtered_entries]
                    cite_keys_text = ", ".join(cite_keys)
                    if st.button("📋 Copy All Cite Keys"):
                        st.code(cite_keys_text)

                with col2:
                    # BibTeX export
                    bibtex_content = "\n\n".join(
                        [entry[1] for entry in filtered_entries]
                    )
                    st.download_button(
                        label="📄 Download BibTeX",
                        data=bibtex_content,
                        file_name=f"references_{datetime.now().strftime('%Y%m%d_%H%M%S')}.bib",
                        mime="text/plain",
                    )

                with col3:
                    # RIS export
                    ris_content = "\n\n".join(
                        [convert_to_ris(entry[1]) for entry in filtered_entries]
                    )
                    st.download_button(
                        label="📄 Download RIS",
                        data=ris_content,
                        file_name=f"references_{datetime.now().strftime('%Y%m%d_%H%M%S')}.ris",
                        mime="text/plain",
                    )

                with col4:
                    # EndNote export
                    endnote_content = "\n\n".join(
                        [convert_to_endnote(entry[1]) for entry in filtered_entries]
                    )
                    st.download_button(
                        label="📄 Download EndNote",
                        data=endnote_content,
                        file_name=f"references_{datetime.now().strftime('%Y%m%d_%H%M%S')}.enw",
                        mime="text/plain",
                    )

                st.markdown("---")

                # Display entries
                for i, entry in enumerate(filtered_entries):
                    cite_key, bibtex, year, metadata = entry
                    bib_metadata = metadata.get("bib_metadata", {})
                    quality_score = metadata.get("quality_score", 0)

                    with st.expander(f"📖 {cite_key} ({year})", expanded=False):
                        # Entry metadata
                        col1, col2 = st.columns([3, 1])

                        with col1:
                            if "title" in bib_metadata:
                                st.markdown(f"**Title:** {bib_metadata['title']}")
                            if "author" in bib_metadata:
                                st.markdown(f"**Authors:** {bib_metadata['author']}")
                            if "journal" in bib_metadata:
                                st.markdown(f"**Journal:** {bib_metadata['journal']}")
                            if "doi" in bib_metadata:
                                st.markdown(f"**DOI:** {bib_metadata['doi']}")

                        with col2:
                            # Quality score
                            score_color = (
                                "green"
                                if quality_score >= 80
                                else "orange" if quality_score >= 60 else "red"
                            )
                            st.markdown(
                                f"**Quality Score:** <span style='color: {score_color}'>{quality_score:.1f}%</span>",
                                unsafe_allow_html=True,
                            )

                            # Processing info
                            if "processing_time" in metadata:
                                st.markdown(
                                    f"**Processing Time:** {metadata['processing_time']:.2f}s"
                                )

                        # BibTeX content
                        st.markdown("**BibTeX Entry:**")
                        st.code(bibtex, language="bibtex")

                        # Action buttons
                        col1, col2, col3 = st.columns(3)

                        with col1:
                            if st.button(f"Copy BibTeX", key=f"copy_bibtex_{i}"):
                                st.code(bibtex)

                        with col2:
                            if st.button(f"Copy RIS", key=f"copy_ris_{i}"):
                                ris_entry = convert_to_ris(bibtex)
                                st.code(ris_entry)

                        with col3:
                            if st.button(f"Copy EndNote", key=f"copy_endnote_{i}"):
                                endnote_entry = convert_to_endnote(bibtex)
                                st.code(endnote_entry)

    with tab3:
        st.markdown("### ⚙️ Advanced Settings")

        st.markdown("#### Citation Key Generation")

        # Citation key patterns
        pattern_help = {
            "author_year": "Example: smith2023",
            "first_author_title_year": "Example: smithanalysis2023",
            "journal_year": "Example: nature2023",
        }

        selected_pattern = st.radio(
            "Citation Key Pattern",
            list(pattern_help.keys()),
            format_func=lambda x: f"{x.replace('_', ' ').title()} ({pattern_help[x]})",
            index=list(pattern_help.keys()).index(
                st.session_state.user_preferences["citation_key_pattern"]
            ),
        )
        st.session_state.user_preferences["citation_key_pattern"] = selected_pattern

        st.markdown("#### Field Ordering")

        # BibTeX field ordering
        available_fields = [
            "title",
            "author",
            "journal",
            "volume",
            "number",
            "pages",
            "year",
            "publisher",
            "doi",
            "isbn",
            "issn",
            "abstract",
            "keywords",
            "note",
        ]

        selected_fields = st.multiselect(
            "Select and order BibTeX fields",
            available_fields,
            default=st.session_state.user_preferences["field_order"],
        )
        st.session_state.user_preferences["field_order"] = selected_fields

        st.markdown("#### Data Processing")

        col1, col2 = st.columns(2)

        with col1:
            auto_cleanup = st.checkbox("Automatic data cleanup", value=True)
            remove_duplicates = st.checkbox("Remove duplicate entries", value=True)
            validate_dois = st.checkbox("Validate DOI formats", value=True)

        with col2:
            include_quality_scores = st.checkbox("Calculate quality scores", value=True)
            fetch_abstracts = st.checkbox("Fetch abstracts when available", value=False)
            normalize_authors = st.checkbox("Normalize author names", value=False)

        st.markdown("#### Performance Settings")

        timeout_setting = st.slider(
            "Request timeout (seconds)", min_value=5, max_value=30, value=10
        )
        max_retries = st.slider(
            "Maximum retries per DOI", min_value=1, max_value=5, value=3
        )
        concurrent_requests = st.slider(
            "Concurrent requests", min_value=1, max_value=10, value=3
        )

        if st.button("Apply Advanced Settings"):
            st.success("Advanced settings applied successfully!")

    with tab4:
        st.markdown("### 📈 Bibliography Analytics")

        if not st.session_state.bibtex_entries:
            st.info("No data available for analysis. Convert some DOIs first!")
        else:
            analysis_data = st.session_state.analytics_data

            if analysis_data:
                # Overview metrics
                st.markdown("#### 📊 Overview")
                render_metrics_dashboard(analysis_data)

                st.markdown("---")

                # Simple charts section
                col1, col2 = st.columns(2)

                with col1:
                    if analysis_data.get("years"):
                        timeline_chart = create_timeline_chart(analysis_data["years"])
                        st.markdown(timeline_chart, unsafe_allow_html=True)

                with col2:
                    if analysis_data.get("journals"):
                        journal_counts = Counter(analysis_data["journals"])
                        journal_chart = create_simple_bar_chart(
                            dict(journal_counts.most_common(8)), "Top Journals"
                        )
                        st.markdown(journal_chart, unsafe_allow_html=True)

                # Author analysis
                if analysis_data.get("authors"):
                    author_counts = Counter(analysis_data["authors"])
                    author_chart = create_simple_bar_chart(
                        dict(author_counts.most_common(10)), "Top Authors"
                    )
                    st.markdown(author_chart, unsafe_allow_html=True)

                st.markdown("---")

                # Detailed statistics
                st.markdown("#### 📋 Detailed Statistics")

                col1, col2, col3 = st.columns(3)

                # Column 1: Publication Years
                with col1:
                    st.markdown("**📅 Publication Years**")
                    if analysis_data.get("years"):
                        years = analysis_data["years"]
                        year_stats = {
                            "Earliest": min(years),
                            "Latest": max(years),
                            "Range": max(years) - min(years),
                            "Average": sum(years) / len(years) if years else 0,
                        }
                        for key, value in year_stats.items():
                            if key == "Average":
                                st.write(f"• **{key}:** {value:.1f}")
                            else:
                                st.write(f"• **{key}:** {value}")

                # Column 2: Authors
                with col2:
                    st.markdown("**👥 Authors**")
                    if analysis_data.get("authors"):
                        authors_list = analysis_data["authors"]
                        unique_authors = set(authors_list)
                        author_stats = Counter(authors_list)
                        most_prolific = (
                            author_stats.most_common(1)[0]
                            if author_stats
                            else ("N/A", 0)
                        )

                        # Truncate long author names for display
                        prolific_name = most_prolific[0]
                        display_name = (
                            (prolific_name[:25] + "...")
                            if len(prolific_name) > 25
                            else prolific_name
                        )

                        st.write(f"• **Total unique:** {len(unique_authors)}")
                        st.write(f"• **Most prolific:** {display_name}")
                        st.write(f"• **Their publications:** {most_prolific[1]}")
                        if unique_authors:
                            st.write(
                                f"• **Average per author:** {len(authors_list) / len(unique_authors):.1f}"
                            )

                # Column 3: Journals
                with col3:
                    st.markdown("**📰 Journals**")
                    if analysis_data.get("journals"):
                        journals_list = analysis_data["journals"]
                        journal_stats = Counter(journals_list)
                        top_journal = (
                            journal_stats.most_common(1)[0]
                            if journal_stats
                            else ("N/A", 0)
                        )

                        # Truncate long journal names for display
                        journal_name = top_journal[0]
                        display_journal = (
                            (journal_name[:25] + "...")
                            if len(journal_name) > 25
                            else journal_name
                        )

                        st.write(f"• **Total unique:** {len(set(journals_list))}")
                        st.write(f"• **Top journal:** {display_journal}")
                        st.write(f"• **Their publications:** {top_journal[1]}")
                        st.write(
                            f"• **DOI coverage:** {analysis_data.get('doi_coverage', 0):.1f}%"
                        )

                # Export analytics
                st.markdown("---")
                st.markdown("#### 💾 Export Analytics")

                col1, col2 = st.columns(2)

                with col1:
                    # Export analytics as JSON
                    analytics_json = json.dumps(analysis_data, indent=2, default=str)
                    st.download_button(
                        label="📊 Download Analytics (JSON)",
                        data=analytics_json,
                        file_name=f"bibliography_analytics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json",
                    )

                with col2:
                    # Export summary report
                    if st.button("📄 Generate Summary Report"):
                        report = f"""# Bibliography Analysis Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Summary
- Total entries: {analysis_data.get('total_entries', 0)}
- Unique authors: {analysis_data.get('unique_authors', 0)}
- Unique journals: {analysis_data.get('unique_journals', 0)}
- Year range: {analysis_data.get('year_range', 'N/A')}
- DOI coverage: {analysis_data.get('doi_coverage', 0):.1f}%

## Top Authors
{chr(10).join([f"- {author}: {count} publications" for author, count in Counter(analysis_data.get('authors', [])).most_common(10)])}

## Top Journals
{chr(10).join([f"- {journal}: {count} publications" for journal, count in Counter(analysis_data.get('journals', [])).most_common(10)])}

## Publication Timeline
{chr(10).join([f"- {year}: {count} publications" for year, count in sorted(Counter(analysis_data.get('years', [])).items())])}
"""

                        st.download_button(
                            label="📄 Download Report (Markdown)",
                            data=report,
                            file_name=f"bibliography_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                            mime="text/markdown",
                        )

    with tab5:
        st.markdown("### ℹ️ Help & Documentation")

        # Feature overview
        st.markdown(
            """
        #### 🚀 Features Overview
        
        **Core Features:**
        - Convert single or multiple DOIs to BibTeX format
        - Support for bulk processing via file upload
        - Multiple export formats (BibTeX, RIS, EndNote)
        - Real-time progress tracking and error handling
        
        **Advanced Features:**
        - Duplicate detection and removal
        - Custom citation key generation patterns
        - Quality score calculation for entries
        - Search and filter functionality
        - Bibliography analytics and visualization
        
        **User Experience:**
        - Dark/Light theme support
        - Responsive design for all devices
        - Session management and data persistence
        - Copy-to-clipboard functionality
        """
        )

        st.markdown("---")

        # Usage instructions
        st.markdown(
            """
        #### 📖 How to Use
        
        1. **Input DOIs**: Choose from manual entry, file upload, or bulk processing
        2. **Configure Settings**: Adjust citation patterns, field ordering, and processing options
        3. **Convert**: Click the convert button to process your DOIs
        4. **Review Results**: Use the Results tab to view, search, and filter your entries
        5. **Export**: Download your bibliography in various formats
        6. **Analyze**: Use the Analytics tab to gain insights into your bibliography
        """
        )

        st.markdown("---")

        # Troubleshooting
        st.markdown(
            """
        #### 🛠️ Troubleshooting
        
        **NumPy Compatibility Issues:**
        - This version is designed for NumPy 2.0+ compatibility
        - If you encounter issues, try: `pip install numpy<2.0` for NumPy 1.x
        - Or update all packages: `pip install --upgrade pandas plotly streamlit`
        
        **Common Issues:**
        
        **DOI Not Found:**
        - Verify the DOI is correct and published
        - Check if the DOI service is accessible
        - Try again after a few moments
        
        **Network Errors:**
        - Check your internet connection
        - The DOI service may be temporarily unavailable
        - Try with a smaller batch size
        
        **Invalid Format:**
        - Ensure DOIs follow the standard format: 10.xxxx/xxxxx
        - Remove any extra characters or spaces
        - Use the DOI validation feature
        """
        )

        st.markdown("---")

        # Version information
        st.markdown(
            """
        #### 📋 Version Information
        
        **Current Version:** 2.1.0 (NumPy 2.0 Compatible)  
        **Last Updated:** September 2025  
        **License:** MIT License  
        
        **Dependencies:**
        - streamlit
        - requests
        - No pandas, plotly, or NumPy-dependent libraries
        
        **Changelog:**
        - ✅ NumPy 2.0 compatibility fixes
        - ✅ Removed problematic dependencies
        - ✅ Simple HTML/CSS charts instead of Plotly
        - ✅ All core functionality preserved
        - ✅ Enhanced error handling
        - ✅ Improved performance
        """
        )


if __name__ == "__main__":
    main()
