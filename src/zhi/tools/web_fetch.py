"""Web fetch tool for zhi."""

from __future__ import annotations

import html
import re
from typing import Any, ClassVar

from zhi.tools.base import BaseTool

_MAX_CONTENT_SIZE = 50 * 1024  # 50KB
_DEFAULT_TIMEOUT = 30


def _strip_html_tags(html_content: str) -> str:
    """Extract text from HTML by stripping tags."""
    # Remove script and style elements
    text = re.sub(
        r"<script[^>]*>.*?</script>",
        "",
        html_content,
        flags=re.DOTALL | re.IGNORECASE,
    )
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
    # Replace common block tags with newlines
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</(p|div|h[1-6]|li|tr)>", "\n", text, flags=re.IGNORECASE)
    # Strip remaining tags
    text = re.sub(r"<[^>]+>", "", text)
    # Decode HTML entities
    text = html.unescape(text)
    # Collapse whitespace
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


class WebFetchTool(BaseTool):
    """Fetch content from a URL."""

    name: ClassVar[str] = "web_fetch"
    description: ClassVar[str] = (
        "Fetch the text content of a web page. "
        "HTML is converted to plain text. "
        "Response capped at 50KB."
    )
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "The URL to fetch.",
            },
        },
        "required": ["url"],
    }
    risky: ClassVar[bool] = False

    def execute(self, **kwargs: Any) -> str:
        import httpx

        url: str = kwargs.get("url", "")
        if not url:
            return "Error: 'url' parameter is required."

        # Basic URL validation
        if not url.startswith(("http://", "https://")):
            return "Error: Invalid URL. Must start with http:// or https://."

        try:
            response = httpx.get(url, timeout=_DEFAULT_TIMEOUT, follow_redirects=True)
        except httpx.TimeoutException:
            return f"Error: Request timed out after {_DEFAULT_TIMEOUT}s."
        except httpx.ConnectError:
            return f"Error: Could not connect to {url}."
        except httpx.RequestError as exc:
            return f"Error: Request failed: {exc}"

        if response.status_code != 200:
            return f"Error: HTTP {response.status_code} for {url}."

        content_type = response.headers.get("content-type", "")
        text = response.text

        # If HTML, strip tags
        is_html = (
            "html" in content_type.lower()
            or text.lstrip().startswith("<!")
            or text.lstrip().startswith("<html")
        )
        if is_html:
            text = _strip_html_tags(text)

        # Truncate
        if len(text) > _MAX_CONTENT_SIZE:
            total = len(response.text)
            text = (
                text[:_MAX_CONTENT_SIZE] + f"\n[truncated, showing first "
                f"50KB of {total}B]"
            )

        if not text.strip():
            return "Page returned no extractable text content."

        return text
