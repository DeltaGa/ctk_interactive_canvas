"""Unit conversion utilities for pixel/millimeter coordinate handling.

Pure functions with no widget dependencies - safe to import anywhere.
Both functions mirror the instance-method API on ``DraggableRectangle``
but operate on plain scalars and accept an explicit ``dpi`` argument,
making them testable without a running canvas.
"""

import logging


def mm_to_px(millimeters: float, dpi: int) -> int:
    """Convert millimeters to pixels at the given DPI resolution.

    Args:
        millimeters: Measurement in millimeters.
        dpi: Dots per inch (e.g. 96 for screen, 300 for print).

    Returns:
        Pixel count as a truncated integer (``int(mm * dpi / 25.4)``).

    Raises:
        Exception: Propagates any arithmetic error (e.g. overflow).
    """
    try:
        return int(millimeters * dpi / 25.4)
    except Exception as e:
        logging.error(f"Failed to convert millimeters to pixels: {e}")
        raise


def px_to_mm(pixels: float, dpi: int) -> float:
    """Convert pixels to millimeters at the given DPI resolution.

    Args:
        pixels: Measurement in pixels.
        dpi: Dots per inch (e.g. 96 for screen, 300 for print).

    Returns:
        Measurement in millimeters as a float (``px * 25.4 / dpi``).

    Raises:
        Exception: Propagates any arithmetic error (e.g. division by zero).
    """
    try:
        return pixels * 25.4 / dpi
    except Exception as e:
        logging.error(f"Failed to convert pixels to millimeters: {e}")
        raise
