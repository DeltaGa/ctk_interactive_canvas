"""
Regression tests for the pointer-capture gesture lock.

These guard against the resize-handle-also-moves bug: when a resize gesture
owns the pointer, stray body ``<B1-Motion>`` events (which Tk routes to the
overlapping rectangle body once the cursor slips off the small handle glyph)
must never translate the rectangle — and vice versa. Only one of move/resize
may own the pointer between ButtonPress and ButtonRelease.
"""

from types import SimpleNamespace


def _event(x, y):
    """Minimal stand-in for a tkinter mouse Event (handlers read only x/y)."""
    return SimpleNamespace(x=x, y=y)


def test_resize_gesture_blocks_body_move(canvas, rect):
    """A claimed resize gesture must suppress body translation entirely."""
    canvas.select_item(canvas.get_item_id(rect))
    before = list(rect)

    # Press on the handle -> claims the "resize" gesture.
    rect.on_resize_click(_event(100, 100))
    assert canvas._active_gesture == "resize"

    # A stray body drag arrives (cursor slipped off the handle). It must be inert.
    rect.on_drag(_event(180, 220))

    assert list(rect) == before  # no diagonal drift


def test_move_gesture_blocks_resize(canvas, rect):
    """A claimed move gesture must suppress handle resizing entirely."""
    canvas.select_item(canvas.get_item_id(rect))
    size_before = rect.get_size()

    # Press on the body -> claims the "move" gesture.
    rect.on_click(_event(50, 50))
    assert canvas._active_gesture == "move"

    # A stray resize drag arrives. It must be inert (size unchanged).
    rect.on_resize_drag(_event(200, 200))

    assert rect.get_size() == size_before


def test_release_clears_gesture(canvas, rect):
    """ButtonRelease must release the capture so the next gesture is free."""
    canvas.select_item(canvas.get_item_id(rect))

    rect.on_resize_click(_event(100, 100))
    assert canvas._active_gesture == "resize"

    canvas._builtin_on_drag_release(_event(100, 100))
    assert canvas._active_gesture is None

    # With the capture cleared, a fresh body move works normally again.
    rect.on_click(_event(0, 0))
    before = rect.get_topleft_pos()
    rect.on_drag(_event(15, 25))
    after = rect.get_topleft_pos()
    assert after == [before[0] + 15, before[1] + 25]


def test_normal_move_still_works(canvas, rect):
    """Sanity: an uncontested body move translates as before."""
    canvas.select_item(canvas.get_item_id(rect))
    rect.on_click(_event(40, 40))
    before = rect.get_topleft_pos()
    rect.on_drag(_event(60, 75))
    after = rect.get_topleft_pos()
    assert after == [before[0] + 20, before[1] + 35]


def test_normal_resize_still_works(canvas, rect):
    """Sanity: an uncontested handle drag resizes as before."""
    canvas.select_item(canvas.get_item_id(rect))
    rect.on_resize_click(_event(100, 100))
    w_before, h_before = rect.get_size()
    rect.on_resize_drag(_event(130, 150))
    w_after, h_after = rect.get_size()
    assert w_after == w_before + 30
    assert h_after == h_before + 50
