"""
Pytest configuration and shared fixtures.
"""

import customtkinter as ctk
import pytest
from ctk_interactive_canvas import InteractiveCanvas


@pytest.fixture()
def app():
    """Create a CTk app instance for testing."""
    app = ctk.CTk()
    yield app
    try:
        app.destroy()
    except:
        pass


@pytest.fixture()
def canvas(app):
    """Create an InteractiveCanvas for testing."""
    canvas = InteractiveCanvas(app, width=600, height=400, bg="white")
    canvas.pack(fill="both", expand=True)
    app.update()
    return canvas


@pytest.fixture()
def rect(canvas):
    """Create a basic DraggableRectangle for testing."""
    return canvas.create_draggable_rectangle(10, 10, 100, 100, outline="blue")


@pytest.fixture()
def multiple_rects(canvas):
    """Create multiple rectangles for testing."""
    rects = []
    for i in range(3):
        rect = canvas.create_draggable_rectangle(
            10 + i * 110, 10, 100 + i * 110, 100, outline="blue"
        )
        rects.append(rect)
    return rects
