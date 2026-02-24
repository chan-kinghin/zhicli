"""Tests for zhi.keybindings module."""

from __future__ import annotations

from unittest.mock import MagicMock

from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys

from zhi.keybindings import create_key_bindings


def _key_set(kb: KeyBindings) -> set[tuple[str | Keys, ...]]:
    """Extract all key tuples from a KeyBindings instance."""
    return {b.keys for b in kb.bindings}


class TestCreateKeyBindings:
    """Test the key bindings factory."""

    def test_returns_key_bindings(self) -> None:
        kb = create_key_bindings()
        assert isinstance(kb, KeyBindings)

    def test_has_enter_binding(self) -> None:
        """Enter is normalized to c-m (Ctrl+M) by prompt_toolkit."""
        kb = create_key_bindings()
        keys = _key_set(kb)
        assert (Keys.ControlM,) in keys

    def test_has_ctrl_j_binding(self) -> None:
        kb = create_key_bindings()
        keys = _key_set(kb)
        assert (Keys.ControlJ,) in keys

    def test_has_ctrl_l_binding(self) -> None:
        kb = create_key_bindings()
        keys = _key_set(kb)
        assert (Keys.ControlL,) in keys

    def test_enter_calls_validate_and_handle(self) -> None:
        kb = create_key_bindings()
        enter_bindings = [b for b in kb.bindings if b.keys == (Keys.ControlM,)]
        assert len(enter_bindings) == 1

        event = MagicMock()
        enter_bindings[0].handler(event)
        event.current_buffer.validate_and_handle.assert_called_once()

    def test_ctrl_j_inserts_newline(self) -> None:
        kb = create_key_bindings()
        ctrl_j_bindings = [b for b in kb.bindings if b.keys == (Keys.ControlJ,)]
        assert len(ctrl_j_bindings) == 1

        event = MagicMock()
        ctrl_j_bindings[0].handler(event)
        event.current_buffer.insert_text.assert_called_once_with("\n")

    def test_ctrl_l_clears_screen(self) -> None:
        kb = create_key_bindings()
        ctrl_l_bindings = [b for b in kb.bindings if b.keys == (Keys.ControlL,)]
        assert len(ctrl_l_bindings) == 1

        event = MagicMock()
        ctrl_l_bindings[0].handler(event)
        event.app.renderer.clear.assert_called_once()

    def test_binding_count(self) -> None:
        """Should have exactly 3 bindings."""
        kb = create_key_bindings()
        assert len(kb.bindings) == 3
