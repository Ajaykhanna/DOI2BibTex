from __future__ import annotations
import time
from typing import Dict, Optional, Tuple
import requests

DEFAULT_TIMEOUT = 10
DEFAULT_MAX_RETRIES = 3


def polite_headers(
    email: str | None = None, accept: str = "application/x-bibtex; charset=utf-8"
) -> Dict[str, str]:
    """Return a polite set of HTTP headers for DOI-to-BibTeX requests.

    Constructs a User-Agent identifying this application and includes an optional
    contact email as recommended by many APIs (e.g. CrossRef). Also sets an
    Accept header suitable for requesting BibTeX by default.

    Parameters
    - email: Optional contact email to include in the User-Agent (e.g. "me@example.com").
    - accept: Value for the Accept header; defaults to "application/x-bibtex; charset=utf-8".

    Returns
    - Dict[str, str]: A headers mapping containing 'User-Agent' and 'Accept'.

    Example
    >>> polite_headers("me@example.com")
    {'User-Agent': 'DOI2BibTeX/2.1.0 (+https://doi2bibtex.streamlit.app/) contact=me@example.com',
     'Accept': 'application/x-bibtex; charset=utf-8'}
    """
    ua = "DOI2BibTeX/2.1.0 (+https://doi2bibtex.streamlit.app/)"
    if email:
        ua += f" contact={email}"
    return {"User-Agent": ua, "Accept": accept}


def get_with_retry(
    url: str,
    headers: Dict[str, str],
    timeout: int = DEFAULT_TIMEOUT,
    max_retries: int = DEFAULT_MAX_RETRIES,
) -> Tuple[Optional[requests.Response], Optional[str]]:
    """Perform an HTTP GET with exponential backoff and respect for Retry-After.

    This function will attempt to GET the given URL using the provided headers.
    It implements:
    - exponential backoff between attempts (starting at 1.0s, doubling each time,
      capped at 16.0s),
    - handling of HTTP 429 (Too Many Requests) by reading the 'Retry-After'
      header (if present and numeric) and sleeping for that many seconds,
    - catching requests.exceptions.RequestException and retrying until the
      configured max_retries is reached.

    Parameters
    - url: Target URL to GET.
    - headers: Dictionary of HTTP headers to send.
    - timeout: Per-request timeout in seconds (default 10).
    - max_retries: Number of retry attempts after the initial try (default 3).

    Returns
    - (response, error_message):
        - response: requests.Response on success, or None if all attempts failed.
        - error_message: None on success, or a string describing the final error.

    Notes
    - On receiving a 429 response the function will sleep according to the
      Retry-After header if present and numeric; otherwise it will use the
      current backoff delay.
    - The function does not raise; it returns (None, error_string) on failure.

    Example
    >>> resp, err = get_with_retry("https://api.example.org/resource", polite_headers())
    """
    backoff = 1.0
    for attempt in range(max_retries + 1):
        try:
            resp = requests.get(url, headers=headers, timeout=timeout)
            # Handle rate limiting
            if resp.status_code == 429:
                retry_after = resp.headers.get("Retry-After")
                delay = (
                    float(retry_after)
                    if retry_after and retry_after.isdigit()
                    else backoff
                )
                time.sleep(delay)
                backoff = min(backoff * 2, 16.0)
                continue
            return resp, None
        except requests.exceptions.RequestException as e:
            err = str(e)
            if attempt == max_retries:
                return None, err
            time.sleep(backoff)
            backoff = min(backoff * 2, 16.0)
    return None, "unknown error"


def get_json_with_retry(
    url: str,
    headers: dict,
    timeout: int = 10,
    max_retries: int = 3,
):
    """GET a URL expecting JSON, with retry/backoff and 429 handling.

    This helper sets the Accept header to "application/json" (in addition to
    any headers passed), then performs a GET using requests.get. Behavior:
    - Uses exponential backoff (starting at 1.0s, doubling each retry, capped at 16.0s).
    - If a 429 status is received, attempts to use the 'Retry-After' header if numeric,
      otherwise uses the backoff delay.
    - Calls resp.raise_for_status() to raise on 4xx/5xx responses (except handled 429).
    - Returns the parsed JSON on success.

    Parameters
    - url: URL to request.
    - headers: Base headers mapping; this function will copy and set Accept: application/json.
    - timeout: Per-request timeout in seconds (default 10).
    - max_retries: Number of retry attempts after the initial try (default 3).

    Returns
    - (json_obj, None) on success, or (None, error_message) on failure. The json_obj
      is the result of resp.json().

    Notes
    - Exceptions are caught and returned as error messages rather than being propagated.
    - Caller should be prepared to handle None/error_message pairs.

    Example
    >>> data, err = get_json_with_retry("https://api.crossref.org/works/10.1000/xyz", polite_headers())
    """
    import requests, time

    h = dict(headers)
    h["Accept"] = "application/json"
    backoff = 1.0
    for attempt in range(max_retries + 1):
        try:
            resp = requests.get(url, headers=h, timeout=timeout)
            if resp.status_code == 429:
                ra = resp.headers.get("Retry-After")
                delay = float(ra) if ra and str(ra).isdigit() else backoff
                time.sleep(delay)
                backoff = min(backoff * 2, 16.0)
                continue
            resp.raise_for_status()
            return resp.json(), None
        except Exception as e:
            if attempt == max_retries:
                return None, str(e)
            time.sleep(backoff)
            backoff = min(backoff * 2, 16.0)
