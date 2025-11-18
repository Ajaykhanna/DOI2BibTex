from __future__ import annotations
import time
import asyncio
import threading
from typing import Dict, Optional, Tuple
import requests
import logging


# Configure logger
logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 10
DEFAULT_MAX_RETRIES = 3


class RateLimiter:
    """
    Token bucket rate limiter for synchronous operations.

    Implements the token bucket algorithm to limit the rate of API requests.
    This helps prevent hitting API rate limits and ensures polite API usage.

    Features:
    - Thread-safe operations
    - Configurable rate and time window
    - Automatic token replenishment
    - Blocking wait() method
    - Non-blocking acquire() method

    Example:
        >>> limiter = RateLimiter(rate=50, per=60)  # 50 requests per 60 seconds
        >>> limiter.wait()  # Blocks until a token is available
        >>> # Make API request
        >>> response = requests.get(url)
    """

    def __init__(self, rate: int = 50, per: int = 60):
        """
        Initialize rate limiter.

        Args:
            rate: Number of requests allowed
            per: Time window in seconds (default 60 = 1 minute)
        """
        self.rate = rate
        self.per = per
        self.allowance = float(rate)  # Current token allowance
        self.last_check = time.monotonic()
        self.lock = threading.RLock()

        logger.info(f"RateLimiter initialized: {rate} requests per {per}s")

    def acquire(self) -> bool:
        """
        Try to acquire a token (non-blocking).

        Returns:
            True if token was acquired, False if rate limit would be exceeded
        """
        with self.lock:
            current = time.monotonic()
            elapsed = current - self.last_check
            self.last_check = current

            # Replenish tokens based on elapsed time
            self.allowance += elapsed * (self.rate / self.per)

            # Cap at maximum rate
            if self.allowance > self.rate:
                self.allowance = self.rate

            # Try to consume a token
            if self.allowance < 1.0:
                return False

            self.allowance -= 1.0
            return True

    def wait(self, timeout: Optional[float] = None) -> bool:
        """
        Block until a token is available (blocking).

        Args:
            timeout: Maximum time to wait in seconds (None = wait forever)

        Returns:
            True if token was acquired, False if timeout occurred
        """
        start_time = time.monotonic()

        while not self.acquire():
            if timeout and (time.monotonic() - start_time) >= timeout:
                return False
            time.sleep(0.1)  # Sleep briefly to avoid busy-waiting

        return True

    def reset(self) -> None:
        """Reset the rate limiter to full allowance."""
        with self.lock:
            self.allowance = float(self.rate)
            self.last_check = time.monotonic()
            logger.debug("RateLimiter reset")

    def get_wait_time(self) -> float:
        """
        Calculate estimated wait time for next token.

        Returns:
            Estimated seconds until next token is available
        """
        with self.lock:
            if self.allowance >= 1.0:
                return 0.0

            # Calculate time needed to replenish one token
            tokens_needed = 1.0 - self.allowance
            time_per_token = self.per / self.rate
            return tokens_needed * time_per_token


class AsyncRateLimiter:
    """
    Async token bucket rate limiter for asynchronous operations.

    Features:
    - Async/await support
    - Asyncio-safe operations
    - Same token bucket algorithm as RateLimiter
    - Efficient async waiting

    Example:
        >>> limiter = AsyncRateLimiter(rate=50, per=60)
        >>> await limiter.wait()  # Async wait for token
        >>> # Make async API request
        >>> async with aiohttp.ClientSession() as session:
        ...     response = await session.get(url)
    """

    def __init__(self, rate: int = 50, per: int = 60):
        """
        Initialize async rate limiter.

        Args:
            rate: Number of requests allowed
            per: Time window in seconds
        """
        self.rate = rate
        self.per = per
        self.allowance = float(rate)
        self.last_check = time.monotonic()
        self.lock = asyncio.Lock()

        logger.info(f"AsyncRateLimiter initialized: {rate} requests per {per}s")

    async def acquire(self) -> bool:
        """
        Try to acquire a token (non-blocking).

        Returns:
            True if token was acquired, False if rate limit would be exceeded
        """
        async with self.lock:
            current = time.monotonic()
            elapsed = current - self.last_check
            self.last_check = current

            # Replenish tokens
            self.allowance += elapsed * (self.rate / self.per)

            # Cap at maximum rate
            if self.allowance > self.rate:
                self.allowance = self.rate

            # Try to consume a token
            if self.allowance < 1.0:
                return False

            self.allowance -= 1.0
            return True

    async def wait(self, timeout: Optional[float] = None) -> bool:
        """
        Async wait until a token is available.

        Args:
            timeout: Maximum time to wait in seconds (None = wait forever)

        Returns:
            True if token was acquired, False if timeout occurred
        """
        start_time = time.monotonic()

        while not await self.acquire():
            if timeout and (time.monotonic() - start_time) >= timeout:
                return False
            await asyncio.sleep(0.1)

        return True

    async def reset(self) -> None:
        """Reset the rate limiter to full allowance."""
        async with self.lock:
            self.allowance = float(self.rate)
            self.last_check = time.monotonic()
            logger.debug("AsyncRateLimiter reset")

    async def get_wait_time(self) -> float:
        """
        Calculate estimated wait time for next token.

        Returns:
            Estimated seconds until next token is available
        """
        async with self.lock:
            if self.allowance >= 1.0:
                return 0.0

            tokens_needed = 1.0 - self.allowance
            time_per_token = self.per / self.rate
            return tokens_needed * time_per_token


class HTTPConnectionPool:
    """
    HTTP connection pool with session reuse for improved performance.

    Features:
    - Persistent HTTP connections (connection reuse)
    - Thread-safe session management
    - Automatic retry configuration
    - Connection pooling with configurable limits
    - Reduced latency via keep-alive connections

    Example:
        >>> pool = HTTPConnectionPool(pool_connections=10, pool_maxsize=20)
        >>> response = pool.get(url, headers=headers, timeout=10)
    """

    def __init__(
        self,
        pool_connections: int = 10,
        pool_maxsize: int = 20,
        max_retries_config: int = 3
    ):
        """
        Initialize connection pool.

        Args:
            pool_connections: Number of connection pools to cache
            pool_maxsize: Maximum number of connections to save in pool
            max_retries_config: Max retries for connection errors
        """
        self.pool_connections = pool_connections
        self.pool_maxsize = pool_maxsize
        self._lock = threading.Lock()

        # Create session with connection pooling
        self._session = requests.Session()

        # Configure connection pool adapter
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=pool_connections,
            pool_maxsize=pool_maxsize,
            max_retries=max_retries_config,
            pool_block=False
        )

        # Mount adapter for both http and https
        self._session.mount('http://', adapter)
        self._session.mount('https://', adapter)

        logger.info(
            f"HTTPConnectionPool initialized: "
            f"pool_connections={pool_connections}, pool_maxsize={pool_maxsize}"
        )

    def get(
        self,
        url: str,
        headers: Dict[str, str],
        timeout: int = DEFAULT_TIMEOUT
    ) -> requests.Response:
        """
        Perform HTTP GET using connection pool.

        Args:
            url: Target URL
            headers: HTTP headers
            timeout: Request timeout in seconds

        Returns:
            requests.Response object

        Raises:
            requests.exceptions.RequestException on failure
        """
        with self._lock:
            return self._session.get(url, headers=headers, timeout=timeout)

    def close(self) -> None:
        """Close all connections in the pool."""
        with self._lock:
            self._session.close()
            logger.info("HTTPConnectionPool closed")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - close connections."""
        self.close()


# Global rate limiter instances for HTTP requests
# CrossRef recommends 50 requests per second, we'll be more conservative
_rate_limiter = RateLimiter(rate=50, per=60)  # 50 requests per minute
_async_rate_limiter = AsyncRateLimiter(rate=50, per=60)

# Global connection pool for session reuse
_connection_pool = HTTPConnectionPool(pool_connections=10, pool_maxsize=20)

logger.info("Global rate limiters and connection pool initialized")


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
    - rate limiting using token bucket algorithm to prevent 429 errors,
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
        # Wait for rate limiter token before making request
        _rate_limiter.wait()

        try:
            # Use connection pool for better performance
            resp = _connection_pool.get(url, headers=headers, timeout=timeout)
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
    - Rate limiting using token bucket algorithm to prevent 429 errors.
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
        # Wait for rate limiter token before making request
        _rate_limiter.wait()

        try:
            # Use connection pool for better performance
            resp = _connection_pool.get(url, headers=h, timeout=timeout)
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
