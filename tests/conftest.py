"""
Pytest configuration and shared fixtures.
"""

import sys
from pathlib import Path

# Ensure the local src/ tree is always resolved first so tests always run
# against the live source instead of any previously installed package.
_SRC = Path(__file__).parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import customtkinter as ctk
import pytest
from ctk_interactive_canvas import InteractiveCanvas


@pytest.fixture(scope="function")
def app():
    """Create a CTk app instance for testing."""
    try:
        app = ctk.CTk()
        app.geometry("600x400")
        yield app
        try:
            app.destroy()
        except Exception:
            raise RuntimeError("Failed to destroy the CTk app instance after testing.")
    except Exception as e:
        if "Can't find a usable tk.tcl" in str(e) or "_tkinter.TclError" in str(type(e)):
            pytest.skip(f"Tkinter not properly configured: {e}")
        raise


@pytest.fixture(scope="function")
def canvas(app):
    """Create an InteractiveCanvas for testing."""
    canvas = InteractiveCanvas(app, width=600, height=400, bg="white")
    canvas.pack(fill="both", expand=True)
    app.update()
    app.update_idletasks()
    yield canvas


@pytest.fixture(scope="function")
def rect(canvas):
    """Create a basic DraggableRectangle for testing."""
    return canvas.create_draggable_rectangle(10, 10, 100, 100, outline="blue")


@pytest.fixture(scope="function")
def multiple_rects(canvas):
    """Create multiple rectangles for testing."""
    rects = []
    for i in range(3):
        rect = canvas.create_draggable_rectangle(
            10 + i * 110, 10, 100 + i * 110, 100, outline="blue"
        )
        rects.append(rect)
    return rects
