"""Web browsing via Playwright (headless Chromium).

Stage 4 used this read-only (``fetch``). Stage 4.5 adds scoped extras:
``extract_structured_data`` (read), ``screenshot`` (read), and the single
confirmed write ``fill_and_submit`` (fills fields then submits, in one page
session). Every method opens a page, acts, and closes — there is no persistent
session across calls, which is why the form fill and its submit are one
operation. Playwright is imported lazily and failures are normalized to
``BrowserError`` so a missing install or unreachable page never crashes a turn.
"""

import base64
import re

_DEFAULT_TIMEOUT_MS = 15000
_MAX_CHARS = 4000


class BrowserError(RuntimeError):
    """A web lookup failed (not installed, navigation error, timeout)."""


class BrowserService:
    """Headless page fetcher with scoped extract / screenshot / form-submit."""

    def __init__(
        self,
        *,
        timeout_ms: int = _DEFAULT_TIMEOUT_MS,
        max_chars: int = _MAX_CHARS,
    ) -> None:
        self._timeout_ms = timeout_ms
        self._max_chars = max_chars

    def fetch(self, url: str) -> str:
        """Return the visible text of ``url`` (truncated). Read-only."""
        if not url.startswith(("http://", "https://")):
            raise BrowserError("Only http(s) URLs are supported.")

        sync_playwright = self._import_playwright()
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                try:
                    page = browser.new_page()
                    page.goto(
                        url, timeout=self._timeout_ms, wait_until="domcontentloaded"
                    )
                    text = page.inner_text("body")
                finally:
                    browser.close()
        except BrowserError:
            raise
        except Exception as exc:  # noqa: BLE001 — normalize Playwright failures
            raise BrowserError(f"Failed to load {url}: {exc}") from exc

        return self._clean(text)

    def extract_structured_data(
        self, url: str, selectors: dict[str, str]
    ) -> dict[str, str]:
        """Return ``{key: text}`` for each CSS ``selector`` found on ``url``.

        Read-only. Missing selectors map to an empty string rather than failing
        the whole extraction.
        """
        self._require_http(url)
        sync_playwright = self._import_playwright()
        result: dict[str, str] = {}
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                try:
                    page = browser.new_page()
                    page.goto(
                        url, timeout=self._timeout_ms, wait_until="domcontentloaded"
                    )
                    for key, selector in selectors.items():
                        element = page.query_selector(selector)
                        text = element.inner_text() if element else ""
                        result[key] = text.strip()[: self._max_chars]
                finally:
                    browser.close()
        except BrowserError:
            raise
        except Exception as exc:  # noqa: BLE001 — normalize Playwright failures
            raise BrowserError(f"Failed to extract from {url}: {exc}") from exc
        return result

    def screenshot(self, url: str) -> str:
        """Return a base64-encoded PNG screenshot of ``url``. Read-only."""
        self._require_http(url)
        sync_playwright = self._import_playwright()
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                try:
                    page = browser.new_page()
                    page.goto(
                        url, timeout=self._timeout_ms, wait_until="domcontentloaded"
                    )
                    png = page.screenshot()
                finally:
                    browser.close()
        except BrowserError:
            raise
        except Exception as exc:  # noqa: BLE001 — normalize Playwright failures
            raise BrowserError(f"Failed to screenshot {url}: {exc}") from exc
        return base64.b64encode(png).decode("ascii")

    def fill_and_submit(
        self,
        url: str,
        fields: dict[str, str],
        *,
        submit_selector: str | None = None,
    ) -> str:
        """Fill form ``fields`` ({selector: value}) on ``url`` and submit.

        A write operation — always gated by confirmation upstream. Submits by
        clicking ``submit_selector`` when given, else pressing Enter in the last
        field. Returns the resulting page's visible text (truncated).
        """
        self._require_http(url)
        if not fields:
            raise BrowserError("fill_and_submit requires at least one field.")
        sync_playwright = self._import_playwright()
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                try:
                    page = browser.new_page()
                    page.goto(
                        url, timeout=self._timeout_ms, wait_until="domcontentloaded"
                    )
                    last_selector = None
                    for selector, value in fields.items():
                        page.fill(selector, value, timeout=self._timeout_ms)
                        last_selector = selector
                    if submit_selector:
                        page.click(submit_selector, timeout=self._timeout_ms)
                    elif last_selector:
                        page.press(last_selector, "Enter")
                    page.wait_for_load_state("domcontentloaded")
                    text = page.inner_text("body")
                finally:
                    browser.close()
        except BrowserError:
            raise
        except Exception as exc:  # noqa: BLE001 — normalize Playwright failures
            raise BrowserError(f"Failed to submit form on {url}: {exc}") from exc
        return self._clean(text)

    @staticmethod
    def _require_http(url: str) -> None:
        if not url.startswith(("http://", "https://")):
            raise BrowserError("Only http(s) URLs are supported.")

    def _clean(self, text: str) -> str:
        collapsed = re.sub(r"\n{3,}", "\n\n", text).strip()
        if len(collapsed) > self._max_chars:
            return collapsed[: self._max_chars] + "\n…[truncated]"
        return collapsed

    @staticmethod
    def _import_playwright():
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:  # pragma: no cover - dependency guard
            raise BrowserError(
                "Web browsing is unavailable: the 'playwright' package is not "
                "installed."
            ) from exc
        return sync_playwright
