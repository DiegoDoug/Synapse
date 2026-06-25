"""Read-only browser integration (Playwright headless).

A thin wrapper that navigates to a URL and extracts its text content. Strictly
read-only in this stage — no form filling, clicking, or navigation side
effects. Playwright is imported lazily so the backend boots without it.
"""

from backend.integrations.browser.service import BrowserService

__all__ = ["BrowserService"]
