"""Read-only web browsing via Playwright (headless Chromium).

``BrowserService.fetch`` navigates to a URL and returns its visible text. It is
deliberately minimal and read-only: it opens a page, reads content, and closes.
Playwright is imported lazily and failures are normalized to ``BrowserError`` so
a missing install or unreachable page never crashes a chat turn.
"""

import re

_DEFAULT_TIMEOUT_MS = 15000
_MAX_CHARS = 4000


class BrowserError(RuntimeError):
    """A web lookup failed (not installed, navigation error, timeout)."""


class BrowserService:
    """Headless, read-only page-content fetcher."""

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
