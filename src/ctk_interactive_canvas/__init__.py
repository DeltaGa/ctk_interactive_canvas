# -*- coding: utf-8 -*-
"""
ctk_interactive_canvas - Interactive canvas widget for CustomTkinter

Provides draggable, resizable rectangles with multi-selection, alignment,
and distribution features on a CustomTkinter canvas.

Author: Tchicdje Kouojip Joram Smith (DeltaGa)
License: MIT
"""

from .interactive_canvas import InteractiveCanvas
from .draggable_rectangle import DraggableRectangle, KeyboardStateManager

__version__ = "0.4.0"
__author__ = "Tchicdje Kouojip Joram Smith (DeltaGa)"
__all__ = ["InteractiveCanvas", "DraggableRectangle", "KeyboardStateManager"]
