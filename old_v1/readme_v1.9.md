# DOI → BibTeX Converter V2
## Developers: Ajay Khanna + Claude 4.1 + ChatGPT5 (V2.0)

> Batch convert DOIs to BibTeX and other formats with advanced customization, analytics, and citation style previews.

<img alt="Logo" src="logo.png" width="88" align="right"/>

[![Streamlit](https://img.shields.io/badge/App-Streamlit-ff4b4b.svg)](https://doi2bibtex.streamlit.app/)
![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)
![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)

---

## Live Demo

* **Live app:** [https://doi2bibtex.streamlit.app/](https://doi2bibtex.streamlit.app/)
* **Repo:** [https://github.com/Ajaykhanna/DOI2BibTex](https://github.com/Ajaykhanna/DOI2BibTex)

---

## Features

* **Batch Conversion**: Convert a single DOI or hundreds at once from a text area or file upload (`.txt`, `.csv`).
* **Robust Fetching**: Uses polite headers and a retry/backoff mechanism to handle network issues.
* **Advanced Validation**: Cleans and validates DOIs, reporting errors inline.
* **Duplicate Detection**: Identifies and flags duplicate DOIs in your input.
* **Custom Citation Keys**:
  * Generate keys using patterns like `author_year` or `first_author_title_year`.
  * Edit all keys in a single text box and apply changes to all exports with one click.
  * Copy all generated keys to the clipboard.
* **Multiple Export Formats**: Download your references as `.bib` (BibTeX), `.ris` (Research Information Systems), or `.enw` (EndNote).
* **Citation Style Previews**: Instantly preview your references in **APA**, **MLA**, and **Chicago** formats.
* **Journal Abbreviation Toggle**: Choose between full journal titles or abbreviated names provided by Crossref.
* **Abstracts Support**: Optionally fetch and include abstracts in your BibTeX, RIS, and EndNote exports.
* **Analytics Dashboard**: Visualize your reference list with charts for publication timeline, top authors, and top journals.
* **Modern UI**:
  * A streamlined interface combining conversion and results.
  * Aggregated outputs for easy copying and review.
  * Light, Gray, and Dark themes.

---

## Quick Start

### Requirements

* Python **3.8+** (3.10+ recommended)
* `pip` (or `conda`)

### Install & Run

```bash
# Clone the repository
git clone https://github.com/Ajaykhanna/DOI2BibTex.git
cd DOI2BibTex

# Install dependencies
pip install streamlit requests pandas

# Run the app
streamlit run streamlit_app.py
```

---

## How to Use

1. **Enter DOIs**: Paste DOIs (separated by commas or newlines) or upload a `.txt`/`.csv` file.
2. **Convert**: Click the "Convert" button. Progress and errors are reported as it runs.
3. **Review Results**:
    * **Cite Keys**: Edit keys in the text box and click **Apply Keys** to update all formats.
    * **BibTeX / Previews**: View the combined BibTeX block or check the APA/MLA/Chicago style previews.
    * **Downloads**: Get your `.bib`, `.ris`, or `.enw` files.
4. **Customize (Optional)**: Use the "Advanced" section to change the citation key pattern, toggle abstracts, or switch to journal abbreviations.
5. **Analyze**: Switch to the "Analytics" tab to see visualizations of your data.

---

## Project Structure

```bash
DOI2BibTex/
├─ streamlit_app.py      # Main Streamlit application
├─ core/                 # Core conversion and utility modules
│  ├─ http.py            # Robust HTTP requests
│  ├─ doi.py             # DOI validation and data extraction
│  ├─ keys.py            # Citation key generation
│  ├─ export.py          # BibTeX, RIS, and ENW formatting
│  ├─ dedupe.py          # Duplicate detection
│  ├─ analytics.py       # Dashboard helper functions
│  └─ cite_styles.py     # APA / MLA / Chicago formatting
├─ tests/                # Unit tests for core modules
├─ README.md
└─ logo.png
```

---

## Configuration

* **Polite Headers**: The app sends a contact email in the `User-Agent` per Crossref guidelines. You can change this in `streamlit_app.py` (`APP_EMAIL`).
* **Timeout & Retries**: These settings are configurable in the UI under **Advanced → Performance**.
* **Themes**: Switch between Light, Gray, and Dark themes in the sidebar.

---

## Development

### Setup

```bash
# Install development and testing dependencies
pip install pytest black isort
```

### Run Tests

```bash
pytest -q
```

### Code Style

```bash
black .
isort .
```

---

## Troubleshooting

* **No BibTeX in response**: The DOI resolver may not have a BibTeX entry for that DOI. Verify the DOI is correct or try again later.
* **Abstract not appearing**: Ensure both **Fetch abstracts** and **Include abstracts in exports** are enabled in the "Advanced" section. Not all entries on Crossref have an abstract.
* **Clipboard API blocked**: Some browsers require a secure (HTTPS) context. The app includes a fallback for other environments.
* **429 / Rate-Limiting Errors**: You are sending too many requests. Reduce your batch size or increase the timeout between requests in the performance settings.

---

## Roadmap

* Official CSL-JSON export and CSL-style rendering
* More style previews (e.g., IEEE, ACS)
* Concurrent requests with cancellation
* Session save/restore
* Enhanced analytics (e.g., co-author networks)

---

## Contributing

PRs are welcome! Please follow these steps:

1. Open an issue to discuss the change or bug.
2. Create a feature branch for your work.
3. Add tests for new functionality.
4. Run `pytest` to ensure all tests pass.
5. Open a pull request with a clear description.

---

## License

This project is licensed under the MIT License.

---

## Credits

* **Crossref API** for providing the DOI metadata.
* **Streamlit** for the application framework.
* **Oren** for the [copy-to-clipboard pattern](https://discuss.streamlit.io/t/new-component-st-copy-a-new-way-to-copy-anything/111713).