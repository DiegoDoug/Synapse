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
