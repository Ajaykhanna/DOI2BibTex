"""
**Author**: Ajay Khanna  
**Date**: Dec.10.2023  
**Place**: UC Merced  
**Lab**: Dr. Isborn  

### 📧 Contact Information

- **Email**: [akhanna2@ucmerced.edu](mailto:akhanna2@ucmerced.edu) / [quantphobia@gmail.com](mailto:quantphobia@gmail.com)
- **GitHub**: [Ajaykhanna](https://github.com/Ajaykhanna) 🐱‍💻
- **Twitter**: [@samdig](https://twitter.com/samdig) 🐦
- **LinkedIn**: [ajay-khanna](https://www.linkedin.com/in/ajay-khanna) 💼
"""

import streamlit as st
import requests
import re

def doi2bib(doi):
    """
    Converts a DOI (Digital Object Identifier) to a BibTeX entry and formats it.

    Args:
        doi (str): The DOI to be converted to a BibTeX entry.

    Returns:
        str: The formatted BibTeX entry, or an error message if the DOI is not found or the service is unavailable.
    """
    BASE_URL = "http://dx.doi.org/"
    url = BASE_URL + doi
    headers = {"Accept": "application/x-bibtex"}
    response = requests.get(url, headers=headers)
    if response.status_code == 404:
        return "DOI not found."
    elif response.status_code != 200:
        return "Service unavailable."

    bibtex = response.content.decode()

    # Extract the citation key
    cite_key_match = re.search(r"@article\{([^,]+),", bibtex)
    cite_key = cite_key_match.group(1) if cite_key_match else "unknown"

    # Reformat BibTeX output to place each field on a new line, with title and author first
    fields = re.findall(r"(\w+)\s*=\s*\{([^}]*)\}", bibtex)
    fields_dict = dict(fields)
    
    # Ordering fields with title and author immediately after the citekey
    ordered_keys = ["title", "author"]
    ordered_fields = [(k, fields_dict[k]) for k in ordered_keys if k in fields_dict]
    
    # Include other fields in the original order excluding title and author
    other_fields = [(k, v) for k, v in fields if k not in ordered_keys]

    formatted_bibtex = f"@article{{{cite_key},\n"
    for key, value in ordered_fields + other_fields:
        formatted_bibtex += f"\t{key} = {{{value}}},\n"
    formatted_bibtex = formatted_bibtex.rstrip(",\n") + "\n}"

    return cite_key, formatted_bibtex

def is_valid_doi(doi):
    """Validate DOI format."""
    return bool(re.match(r"10.\d{4,9}/[-._;()/:A-Z0-9]+", doi, re.IGNORECASE))

def extract_year(bibtex):
    """Extract the year from a BibTeX entry."""
    match = re.search(r"year\\s*=\\s*{(\\d{4})}", bibtex)
    return int(match.group(1)) if match else 0  # Return 0 if no year is found

# Streamlit interface
st.set_page_config(
    page_title="DOI to BibTeX Converter", page_icon=":books:", layout="wide"
)
st.markdown(
    """
<style>
.css-18rr39y {
    font-size: 3rem;
    font-weight: bold;
    color: #333;
    text-align: center;
    margin-bottom: 1rem;
}
.css-19bqh2r {
    font-size: 1.2rem;
    font-weight: bold;
    color: #333;
    text-align: center;
    margin-bottom: 2rem;
}
.css-18rr39y input[type="text"] {
    font-size: 1.2rem;
    padding: 0.5rem 1rem;
    border-radius: 0.25rem;
    border: 1px solid #ccc;
    width: 50%;
}
.css-18rr39y button {
    font-size: 1.2rem;
    padding: 0.5rem 1rem;
    border-radius: 0.25rem;
    border: none;
    background-color: #4CAF50;
    color: #fff;
    cursor: pointer;
}
.css-18rr39y button:hover {
    background-color: #3e8e41;
}
.css-18rr39y pre {
    font-size: 1rem;
    padding: 1rem;
    border-radius: 0.25rem;
    border: 1px solid #ccc;
    overflow-x: auto;
    white-space: pre-wrap;
}
</style>
""",
    unsafe_allow_html=True,
)

st.title("DOI to BibTeX Converter")
doi_input = st.text_input("Enter DOIs (separated by commas)", value="10.1000/xyz123")
doi_list = [doi.strip() for doi in doi_input.split(",") if is_valid_doi(doi.strip())]

if st.button("Convert DOIs to BibTeX"):
    dois = doi_list
    cite_keys = []
    bibtex_result = ""
    for doi in dois:
        cite_key, bibtex = doi2bib(doi)
        if "DOI not found" not in bibtex and "Service unavailable" not in bibtex:
            bibtex_result += bibtex + "\n\n"
        else:
            bibtex_result += bibtex + "\n"
            cite_keys.append(cite_key)


    if bibtex_result:
        bibtex_formatted = st.code(bibtex_result, language="plaintext")
    
    else:
        st.write("No valid DOIs found.")

