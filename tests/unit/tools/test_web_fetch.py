"""Tests for web_fetch tool."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from zhi.tools.web_fetch import WebFetchTool, _strip_html_tags


def _make_response(
    status_code: int = 200,
    text: str = "",
    content_type: str = "text/plain",
    is_redirect: bool = False,
) -> MagicMock:
    """Create a mock httpx Response with common defaults."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = text
    resp.headers = {"content-type": content_type}
    resp.is_redirect = is_redirect
    return resp


class TestWebFetchSuccess:
    def test_fetch_plain_text(self) -> None:
        mock_response = _make_response(text="Hello, world!")

        tool = WebFetchTool()
        with patch("httpx.get", return_value=mock_response):
            result = tool.execute(url="https://example.com/text")
        assert result == "Hello, world!"

    def test_fetch_html_strips_tags(self) -> None:
        mock_response = _make_response(
            text="<html><body><h1>Title</h1><p>Content here.</p></body></html>",
            content_type="text/html",
        )

        tool = WebFetchTool()
        with patch("httpx.get", return_value=mock_response):
            result = tool.execute(url="https://example.com")
        assert "Title" in result
        assert "Content here." in result
        assert "<h1>" not in result


class TestWebFetch404:
    def test_non_200_status(self) -> None:
        mock_response = _make_response(status_code=404)

        tool = WebFetchTool()
        with patch("httpx.get", return_value=mock_response):
            result = tool.execute(url="https://example.com/missing")
        assert "Error" in result
        assert "404" in result


class TestWebFetchTimeout:
    def test_timeout_error(self) -> None:
        import httpx

        tool = WebFetchTool()
        with patch("httpx.get", side_effect=httpx.TimeoutException("timeout")):
            result = tool.execute(url="https://example.com")
        assert "Error" in result
        assert "timed out" in result.lower()


class TestWebFetchInvalidUrl:
    def test_missing_url(self) -> None:
        tool = WebFetchTool()
        result = tool.execute(url="")
        assert "Error" in result

    def test_no_scheme(self) -> None:
        tool = WebFetchTool()
        result = tool.execute(url="example.com")
        assert "Error" in result
        assert "Invalid URL" in result


class TestWebFetchConnectionError:
    def test_connection_error(self) -> None:
        import httpx

        tool = WebFetchTool()
        with patch("httpx.get", side_effect=httpx.ConnectError("refused")):
            result = tool.execute(url="https://unreachable.example.com")
        assert "Error" in result
        assert "connect" in result.lower()


class TestWebFetchTruncation:
    def test_truncates_large_content(self) -> None:
        mock_response = _make_response(text="x" * (100 * 1024))

        tool = WebFetchTool()
        with patch("httpx.get", return_value=mock_response):
            result = tool.execute(url="https://example.com/large")
        assert "truncated" in result
        assert len(result) <= 60 * 1024  # 50KB + truncation message


class TestWebFetchSSRFRedirect:
    """Test that SSRF via redirect is blocked."""

    def test_redirect_to_private_ip_blocked(self) -> None:
        redirect_resp = MagicMock()
        redirect_resp.is_redirect = True
        redirect_resp.headers = {"location": "http://127.0.0.1/secrets"}
        redirect_resp.next_request = MagicMock()
        redirect_resp.next_request.url = "http://127.0.0.1/secrets"

        tool = WebFetchTool()
        with patch("httpx.get", return_value=redirect_resp):
            result = tool.execute(url="https://evil.example.com")
        assert "Error" in result
        assert "internal" in result.lower() or "private" in result.lower()

    def test_redirect_to_metadata_blocked(self) -> None:
        redirect_resp = MagicMock()
        redirect_resp.is_redirect = True
        redirect_resp.headers = {"location": "http://metadata.google.internal/"}
        redirect_resp.next_request = MagicMock()
        redirect_resp.next_request.url = "http://metadata.google.internal/"

        tool = WebFetchTool()
        with patch("httpx.get", return_value=redirect_resp):
            result = tool.execute(url="https://evil.example.com")
        assert "Error" in result
        assert "internal" in result.lower() or "private" in result.lower()

    def test_too_many_redirects(self) -> None:
        redirect_resp = MagicMock()
        redirect_resp.is_redirect = True
        redirect_resp.headers = {"location": "https://example.com/loop"}
        redirect_resp.next_request = MagicMock()
        redirect_resp.next_request.url = "https://example.com/loop"

        tool = WebFetchTool()
        with patch("httpx.get", return_value=redirect_resp):
            result = tool.execute(url="https://example.com/start")
        assert "Error" in result
        assert "redirects" in result.lower()

    def test_safe_redirect_followed(self) -> None:
        redirect_resp = MagicMock()
        redirect_resp.is_redirect = True
        redirect_resp.headers = {"location": "https://example.com/final"}
        redirect_resp.next_request = MagicMock()
        redirect_resp.next_request.url = "https://example.com/final"

        final_resp = _make_response(text="Final content")

        call_count = 0

        def side_effect(*args: object, **kwargs: object) -> MagicMock:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return redirect_resp
            return final_resp

        tool = WebFetchTool()
        with patch("httpx.get", side_effect=side_effect):
            result = tool.execute(url="https://example.com/start")
        assert result == "Final content"


class TestStripHtmlTags:
    def test_strips_script_tags(self) -> None:
        html = "<script>alert('xss')</script><p>Safe text</p>"
        result = _strip_html_tags(html)
        assert "alert" not in result
        assert "Safe text" in result

    def test_strips_style_tags(self) -> None:
        html = "<style>body{color:red}</style><p>Content</p>"
        result = _strip_html_tags(html)
        assert "color" not in result
        assert "Content" in result

    def test_preserves_entities(self) -> None:
        html = "<p>A &amp; B &lt; C</p>"
        result = _strip_html_tags(html)
        assert "A & B < C" in result
