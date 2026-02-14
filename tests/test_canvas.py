"""
Tests for InteractiveCanvas.
"""

import pytest
from ctk_interactive_canvas import InteractiveCanvas


def test_canvas_creation(app):
    """Test basic canvas creation."""
    canvas = InteractiveCanvas(app, width=600, height=400)
    assert canvas.winfo_width() >= 0
    assert canvas.dpi == 300


def test_create_rectangle(canvas):
    """Test rectangle creation."""
    rect = canvas.create_draggable_rectangle(10, 10, 100, 100, outline='blue')
    assert rect is not None
    assert len(canvas.objects) == 1


def test_selection(canvas, rect):
    """Test selection operations."""
    item_id = canvas.get_item_id(rect)
    
    canvas.select_item(item_id)
    assert len(canvas.get_selected()) == 1
    assert rect.get_is_selected() is True
    
    canvas.deselect_item(item_id)
    assert len(canvas.get_selected()) == 0
    assert rect.get_is_selected() is False


def test_delete_rectangle(canvas, rect):
    """Test rectangle deletion."""
    item_id = canvas.get_item_id(rect)
    assert len(canvas.objects) == 1
    
    canvas.delete_draggable_rectangle(item_id)
    assert len(canvas.objects) == 0


def test_select_all(canvas, multiple_rects):
    """Test select all functionality."""
    canvas.select_all()
    assert len(canvas.get_selected()) == 3
    for rect in multiple_rects:
        assert rect.get_is_selected() is True


def test_deselect_all(canvas, multiple_rects):
    """Test deselect all functionality."""
    canvas.select_all()
    canvas.deselect_all()
    assert len(canvas.get_selected()) == 0
    for rect in multiple_rects:
        assert rect.get_is_selected() is False
