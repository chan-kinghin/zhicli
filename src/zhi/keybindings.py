"""Key bindings for the zhi REPL.

Provides prompt_toolkit KeyBindings:
- Enter: submit input
- Ctrl+J: insert newline (multi-line editing)
- Ctrl+L: clear screen
"""

from __future__ import annotations

from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.key_binding.key_processor import KeyPressEvent


def create_key_bindings() -> KeyBindings:
    """Create key bindings for the zhi REPL.

    - Enter: submit the current input
    - Ctrl+J: insert a newline for multi-line editing
    - Ctrl+L: clear the screen
    """
    kb = KeyBindings()

    @kb.add("enter")
    def _submit(event: KeyPressEvent) -> None:
        """Submit the buffer content."""
        event.current_buffer.validate_and_handle()

    @kb.add("c-j")
    def _newline(event: KeyPressEvent) -> None:
        """Insert a newline character."""
        event.current_buffer.insert_text("\n")

    @kb.add("c-l")
    def _clear_screen(event: KeyPressEvent) -> None:
        """Clear the terminal screen."""
        event.app.renderer.clear()

    return kb
