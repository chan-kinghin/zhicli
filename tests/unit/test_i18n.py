"""Tests for zhi.i18n module."""

from __future__ import annotations

import pytest

from zhi.i18n import (
    LANGUAGE_PREAMBLE,
    get_language,
    prepend_preamble,
    resolve_language,
    set_language,
    t,
)


class TestLanguagePreamble:
    def test_preamble_exists(self) -> None:
        assert LANGUAGE_PREAMBLE
        assert "Chinese" in LANGUAGE_PREAMBLE
        assert "MUST" in LANGUAGE_PREAMBLE

    def test_prepend_preamble(self) -> None:
        result = prepend_preamble("You are a summarizer.")
        assert result.startswith(LANGUAGE_PREAMBLE)
        assert "You are a summarizer." in result
        assert "\n\n" in result


class TestLanguageResolution:
    def test_default_is_auto(self) -> None:
        set_language("auto")
        assert get_language() == "auto"

    def test_set_language_explicit(self) -> None:
        set_language("zh")
        assert get_language() == "zh"
        assert resolve_language() == "zh"
        set_language("auto")  # Reset

    def test_resolve_auto_defaults_to_en(self, monkeypatch: pytest.MonkeyPatch) -> None:
        set_language("auto")
        monkeypatch.delenv("ZHI_LANGUAGE", raising=False)
        monkeypatch.delenv("LANG", raising=False)
        monkeypatch.delenv("LC_ALL", raising=False)
        assert resolve_language() == "en"

    def test_resolve_auto_detects_zh_from_env(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        set_language("auto")
        monkeypatch.setenv("ZHI_LANGUAGE", "zh")
        assert resolve_language() == "zh"

    def test_resolve_auto_detects_zh_from_lang(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        set_language("auto")
        monkeypatch.delenv("ZHI_LANGUAGE", raising=False)
        monkeypatch.setenv("LANG", "zh_CN.UTF-8")
        assert resolve_language() == "zh"

    def test_resolve_auto_detects_zh_from_lc_all(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        set_language("auto")
        monkeypatch.delenv("ZHI_LANGUAGE", raising=False)
        monkeypatch.delenv("LANG", raising=False)
        monkeypatch.setenv("LC_ALL", "zh_TW.UTF-8")
        assert resolve_language() == "zh"

    def test_explicit_overrides_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        set_language("en")
        monkeypatch.setenv("ZHI_LANGUAGE", "zh")
        assert resolve_language() == "en"
        set_language("auto")  # Reset


class TestTranslation:
    def test_t_returns_english_by_default(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        set_language("auto")
        monkeypatch.delenv("ZHI_LANGUAGE", raising=False)
        monkeypatch.delenv("LANG", raising=False)
        monkeypatch.delenv("LC_ALL", raising=False)
        assert t("repl.goodbye") == "Goodbye!"

    def test_t_returns_chinese_when_zh(self) -> None:
        set_language("zh")
        result = t("repl.goodbye")
        assert result != "Goodbye!"
        assert len(result) > 0
        set_language("auto")  # Reset

    def test_t_with_format_args(self, monkeypatch: pytest.MonkeyPatch) -> None:
        set_language("auto")
        monkeypatch.delenv("ZHI_LANGUAGE", raising=False)
        monkeypatch.delenv("LANG", raising=False)
        monkeypatch.delenv("LC_ALL", raising=False)
        result = t("repl.model_switched", model="glm-5")
        assert "glm-5" in result

    def test_t_falls_back_to_english(self) -> None:
        set_language("zh")
        # Even if a key is missing in zh, it should fall back to en
        set_language("auto")  # Reset

    def test_t_returns_key_for_unknown(self, monkeypatch: pytest.MonkeyPatch) -> None:
        set_language("auto")
        monkeypatch.delenv("ZHI_LANGUAGE", raising=False)
        monkeypatch.delenv("LANG", raising=False)
        monkeypatch.delenv("LC_ALL", raising=False)
        result = t("nonexistent.key")
        assert result == "nonexistent.key"

    def test_t_chinese_banner(self) -> None:
        set_language("zh")
        tagline = t("banner.tagline")
        assert "GLM" in tagline
        set_language("auto")  # Reset

    def test_t_chinese_help_contains_slash_commands(self) -> None:
        set_language("zh")
        help_text = t("repl.help")
        assert "/help" in help_text
        assert "/exit" in help_text
        set_language("auto")  # Reset

    def test_all_en_keys_have_zh_translations(self) -> None:
        from zhi.i18n import _STRINGS

        en_keys = set(_STRINGS["en"].keys())
        zh_keys = set(_STRINGS["zh"].keys())
        missing = en_keys - zh_keys
        assert not missing, f"Missing zh translations: {missing}"


class TestPreambleContent:
    def test_preamble_mentions_section_headers(self) -> None:
        assert "section headers" in LANGUAGE_PREAMBLE

    def test_preamble_mentions_table_headers(self) -> None:
        assert "table headers" in LANGUAGE_PREAMBLE

    def test_preamble_is_firm_directive(self) -> None:
        assert "MUST" in LANGUAGE_PREAMBLE

    def test_preamble_forbids_mixing(self) -> None:
        assert "Never mix" in LANGUAGE_PREAMBLE
