"""Web fetch tool for zhi."""

from __future__ import annotations

import html
import ipaddress
import re
from typing import Any, ClassVar
from urllib.parse import urlparse

from zhi.tools.base import BaseTool

_MAX_CONTENT_SIZE = 50 * 1024  # 50KB
_DEFAULT_TIMEOUT = 30
_USER_AGENT = "zhi-cli/1.0"

# Blocked hostnames for SSRF protection
_BLOCKED_HOSTS = frozenset(
    {
        "localhost",
        "metadata.google.internal",
        "metadata",
    }
)


def _is_private_or_reserved(hostname: str) -> bool:
    """Check if a hostname resolves to a private/reserved IP address."""
    # Block known dangerous hostnames
    if hostname.lower() in _BLOCKED_HOSTS:
        return True

    # Check if the hostname is an IP address in a private/reserved range
    try:
        addr = ipaddress.ip_address(hostname)
        return addr.is_private or addr.is_reserved or addr.is_loopback
    except ValueError:
        pass

    return False


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


_MAX_REDIRECTS = 5


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

    def _validate_url(self, url: str) -> str | None:
        """Validate a URL for SSRF. Returns error string or None if OK."""
        try:
            parsed = urlparse(url)
            hostname = parsed.hostname or ""
            if _is_private_or_reserved(hostname):
                return "Error: Access to internal/private addresses is not allowed."
        except ValueError:
            return "Error: Could not parse URL."
        return None

    def execute(self, **kwargs: Any) -> str:
        import httpx

        url: str = kwargs.get("url", "")
        if not url:
            return "Error: 'url' parameter is required."

        # Basic URL validation
        if not url.startswith(("http://", "https://")):
            return "Error: Invalid URL. Must start with http:// or https://."

        # SSRF protection: block private/internal addresses
        ssrf_err = self._validate_url(url)
        if ssrf_err:
            return ssrf_err

        # Manual redirect handling to validate each hop against SSRF
        try:
            current_url = url
            for _hop in range(_MAX_REDIRECTS):
                response = httpx.get(
                    current_url,
                    timeout=_DEFAULT_TIMEOUT,
                    follow_redirects=False,
                    headers={"User-Agent": _USER_AGENT},
                )
                if response.is_redirect:
                    location = response.headers.get("location", "")
                    if not location:
                        return "Error: Redirect with no Location header."
                    # Resolve relative redirects
                    if response.next_request:
                        redirect_url = response.next_request.url
                    else:
                        redirect_url = location
                    redirect_str = str(redirect_url)
                    ssrf_err = self._validate_url(redirect_str)
                    if ssrf_err:
                        return ssrf_err
                    current_url = redirect_str
                else:
                    break
            else:
                return f"Error: Too many redirects (>{_MAX_REDIRECTS})."
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
