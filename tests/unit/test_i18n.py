"""Tests for zhi.i18n module."""

from __future__ import annotations

import pytest

from zhi.i18n import (
    ASK_USER_PREAMBLE,
    CHAT_SYSTEM_PROMPT,
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

    def test_prepend_preamble_without_ask_user(self) -> None:
        result = prepend_preamble("Skill prompt.", has_ask_user=False)
        assert ASK_USER_PREAMBLE not in result
        assert LANGUAGE_PREAMBLE in result
        assert "Skill prompt." in result

    def test_prepend_preamble_with_ask_user(self) -> None:
        result = prepend_preamble("Skill prompt.", has_ask_user=True)
        assert LANGUAGE_PREAMBLE in result
        assert ASK_USER_PREAMBLE in result
        assert "Skill prompt." in result
        # Order: language preamble first, then ask_user, then skill prompt
        lang_idx = result.index(LANGUAGE_PREAMBLE)
        ask_idx = result.index(ASK_USER_PREAMBLE)
        skill_idx = result.index("Skill prompt.")
        assert lang_idx < ask_idx < skill_idx


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
        monkeypatch.setattr("zhi.i18n._get_system_locale", lambda: None)
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
        monkeypatch.setattr("zhi.i18n._get_system_locale", lambda: None)
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
        monkeypatch.setattr("zhi.i18n._get_system_locale", lambda: None)
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
        monkeypatch.setattr("zhi.i18n._get_system_locale", lambda: None)
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


class TestAskUserPreamble:
    def test_preamble_exists(self) -> None:
        assert ASK_USER_PREAMBLE
        assert len(ASK_USER_PREAMBLE) > 0

    def test_preamble_mentions_ask_user(self) -> None:
        assert "ask_user" in ASK_USER_PREAMBLE

    def test_preamble_mentions_ambiguous(self) -> None:
        assert "ambiguous" in ASK_USER_PREAMBLE

    def test_preamble_forbids_guessing(self) -> None:
        assert "Never guess" in ASK_USER_PREAMBLE


class TestWindowsLocaleDetection:
    def test_resolve_detects_zh_from_locale_module(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """On Windows, LANG/LC_ALL are unset. Fallback to locale module."""
        set_language("auto")
        monkeypatch.delenv("ZHI_LANGUAGE", raising=False)
        monkeypatch.delenv("LANG", raising=False)
        monkeypatch.delenv("LC_ALL", raising=False)
        monkeypatch.setattr("zhi.i18n._get_system_locale", lambda: "zh_CN")
        assert resolve_language() == "zh"

    def test_resolve_defaults_en_when_locale_not_zh(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        set_language("auto")
        monkeypatch.delenv("ZHI_LANGUAGE", raising=False)
        monkeypatch.delenv("LANG", raising=False)
        monkeypatch.delenv("LC_ALL", raising=False)
        monkeypatch.setattr("zhi.i18n._get_system_locale", lambda: "en_US")
        assert resolve_language() == "en"

    def test_resolve_defaults_en_when_locale_returns_none(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        set_language("auto")
        monkeypatch.delenv("ZHI_LANGUAGE", raising=False)
        monkeypatch.delenv("LANG", raising=False)
        monkeypatch.delenv("LC_ALL", raising=False)
        monkeypatch.setattr("zhi.i18n._get_system_locale", lambda: None)
        assert resolve_language() == "en"


class TestChatSystemPrompt:
    def test_prompt_exists(self) -> None:
        assert CHAT_SYSTEM_PROMPT
        assert len(CHAT_SYSTEM_PROMPT) > 0

    def test_prompt_mentions_ask_user(self) -> None:
        assert "ask_user" in CHAT_SYSTEM_PROMPT

    def test_prompt_mentions_skill_create(self) -> None:
        assert "skill_create" in CHAT_SYSTEM_PROMPT
