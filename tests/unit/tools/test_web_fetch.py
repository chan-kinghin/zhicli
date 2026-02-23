"""Tests for web_fetch tool."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from zhi.tools.web_fetch import WebFetchTool, _strip_html_tags


class TestWebFetchSuccess:
    def test_fetch_plain_text(self) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "Hello, world!"
        mock_response.headers = {"content-type": "text/plain"}

        tool = WebFetchTool()
        with patch("httpx.get", return_value=mock_response):
            result = tool.execute(url="https://example.com/text")
        assert result == "Hello, world!"

    def test_fetch_html_strips_tags(self) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = (
            "<html><body><h1>Title</h1><p>Content here.</p></body></html>"
        )
        mock_response.headers = {"content-type": "text/html"}

        tool = WebFetchTool()
        with patch("httpx.get", return_value=mock_response):
            result = tool.execute(url="https://example.com")
        assert "Title" in result
        assert "Content here." in result
        assert "<h1>" not in result


class TestWebFetch404:
    def test_non_200_status(self) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 404

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
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "x" * (100 * 1024)
        mock_response.headers = {"content-type": "text/plain"}

        tool = WebFetchTool()
        with patch("httpx.get", return_value=mock_response):
            result = tool.execute(url="https://example.com/large")
        assert "truncated" in result
        assert len(result) <= 60 * 1024  # 50KB + truncation message


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
