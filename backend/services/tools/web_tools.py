"""Read-only web lookup tool backed by the headless BrowserService."""

from typing import Any

from backend.integrations.browser.service import BrowserError
from backend.services.tools.base import Tool, ToolContext


class WebFetchTool(Tool):
    """Fetch and extract the readable text of a public web page."""

    name = "web_fetch"
    description = (
        "Fetch a public web page by URL and return its visible text. "
        "Read-only: use for looking up information, not for taking actions."
    )
    parameters = {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "Absolute http(s) URL to load.",
            }
        },
        "required": ["url"],
    }

    def run(self, arguments: dict[str, Any], context: ToolContext) -> str:
        url = (arguments.get("url") or "").strip()
        if not url:
            return "No URL provided."
        if context.browser is None:
            return "Web browsing is not available in this environment."
        try:
            return context.browser.fetch(url)
        except BrowserError as exc:
            return f"Could not fetch the page: {exc}"


class ExtractStructuredDataTool(Tool):
    """Scrape specific fields from a page using CSS selectors. Read-only."""

    name = "extract_structured_data"
    description = (
        "Extract structured fields from a public web page. Provide 'selectors' "
        "as a map of field name → CSS selector; returns each field's text. "
        "Read-only."
    )
    parameters = {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "Absolute http(s) URL to load."},
            "selectors": {
                "type": "object",
                "description": "Map of field name → CSS selector to read.",
            },
        },
        "required": ["url", "selectors"],
    }

    def run(self, arguments: dict[str, Any], context: ToolContext) -> str:
        url = (arguments.get("url") or "").strip()
        selectors = arguments.get("selectors")
        if not url or not isinstance(selectors, dict) or not selectors:
            return "extract_structured_data requires 'url' and a 'selectors' object."
        if context.browser is None:
            return "Web browsing is not available in this environment."
        try:
            data = context.browser.extract_structured_data(url, selectors)
        except BrowserError as exc:
            return f"Could not extract from the page: {exc}"
        if not any(data.values()):
            return "No matching content found for the given selectors."
        return "\n".join(f"- {key}: {value or '(empty)'}" for key, value in data.items())


class ScreenshotTool(Tool):
    """Capture a screenshot of a page. Read-only.

    Note: the tool-use loop carries text, so this returns a confirmation with
    the image's byte size rather than the pixels themselves. Feeding the image
    into the model's context is a future multimodal enhancement.
    """

    name = "take_screenshot"
    description = (
        "Capture a screenshot of a public web page. Confirms capture and the "
        "image size; the image itself is not yet returned to the model."
    )
    parameters = {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "Absolute http(s) URL to load."},
        },
        "required": ["url"],
    }

    def run(self, arguments: dict[str, Any], context: ToolContext) -> str:
        url = (arguments.get("url") or "").strip()
        if not url:
            return "No URL provided."
        if context.browser is None:
            return "Web browsing is not available in this environment."
        try:
            encoded = context.browser.screenshot(url)
        except BrowserError as exc:
            return f"Could not screenshot the page: {exc}"
        approx_bytes = len(encoded) * 3 // 4
        return f"Captured a screenshot of {url} ({approx_bytes} bytes, PNG)."
