"""Keyboard modifier state tracking for canvas interaction.

Provides ``KeyboardStateManager``, a lightweight object that tracks the live
press/release state of Shift, Alt, and Ctrl keys for a single canvas instance.
One manager is created per canvas on first ``DraggableRectangle`` construction
and stored on ``canvas._keyboard_state`` so subsequent rectangles share it.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tkinter import Event


class KeyboardStateManager:
    """Manages keyboard modifier state per canvas instance."""

    def __init__(self) -> None:
        """Initialize keyboard state tracking."""
        self.shift_held: bool = False
        self.alt_held: bool = False
        self.ctrl_held: bool = False

    def on_shift_press(self, event: "Event") -> None:
        """Handle Shift key press."""
        self.shift_held = True

    def on_shift_release(self, event: "Event") -> None:
        """Handle Shift key release."""
        self.shift_held = False

    def on_alt_press(self, event: "Event") -> None:
        """Handle Alt key press."""
        self.alt_held = True

    def on_alt_release(self, event: "Event") -> None:
        """Handle Alt key release."""
        self.alt_held = False

    def on_ctrl_press(self, event: "Event") -> None:
        """Handle Ctrl key press."""
        self.ctrl_held = True

    def on_ctrl_release(self, event: "Event") -> None:
        """Handle Ctrl key release."""
        self.ctrl_held = False
