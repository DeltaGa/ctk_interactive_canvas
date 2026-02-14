"""
Interactive Canvas Widget for CustomTkinter

Provides a canvas with built-in support for draggable rectangles, multi-selection,
drag-to-select, panning, and keyboard shortcuts.

Author: Tchicdje Kouojip Joram Smith (DeltaGa)
Created: Tue Aug 6, 2024
"""

from tkinter import Event
from typing import Any, Callable, Dict, List, Optional

import customtkinter as ctk

from .draggable_rectangle import DraggableRectangle


class InteractiveCanvas(ctk.CTkCanvas):
    """
    Extended CTkCanvas with interactive selection and manipulation features.

    Supports:
    - Multi-selection (shift-click, drag-select)
    - Panning (middle mouse or space + drag)
    - Keyboard shortcuts (Delete key)
    - Callbacks for selection events
    """

    def __init__(
        self,
        master: Optional[Any] = None,
        select_callback: Optional[Callable[[], None]] = None,
        deselect_callback: Optional[Callable[[], None]] = None,
        delete_callback: Optional[Callable[[], None]] = None,
        select_outline_color: str = "#16fff6",
        dpi: int = 300,
        create_bindings: bool = True,
        **kwargs: Any,
    ) -> None:
        """
        Initialize an InteractiveCanvas.

        Args:
            master: Parent widget
            select_callback: Called when objects are selected
            deselect_callback: Called when objects are deselected
            delete_callback: Called when Delete key is pressed (overrides default)
            select_outline_color: Color for selected object outlines
            dpi: Dots per inch for coordinate conversions
            create_bindings: Whether to create default mouse/keyboard bindings
            **kwargs: Additional arguments passed to CTkCanvas
        """
        super().__init__(master, **kwargs)

        # Callbacks - use lambda:None as safe default instead of mutable default
        self.select_callback = select_callback if select_callback is not None else lambda: None
        self.deselect_callback = (
            deselect_callback if deselect_callback is not None else lambda: None
        )
        self.delete_callback = delete_callback if delete_callback is not None else lambda: None

        self.select_outline_color = select_outline_color
        self.selected_objects: Dict[int, DraggableRectangle] = {}
        self.objects: Dict[int, DraggableRectangle] = {}
        self.dpi = dpi

        # Selection state
        self.start_x: Optional[float] = None
        self.start_y: Optional[float] = None
        self.selection_rect: Optional[int] = None
        self.dragging: bool = False
        self.panning: bool = False

        # ID management
        self.next_item_id: int = 0

        if create_bindings:
            self._create_bindings()

    def _create_bindings(self) -> None:
        """Create default mouse and keyboard bindings."""
        self.bind("<Button-1>", self.on_click)
        self.bind("<B1-Motion>", self.on_drag_select)
        self.bind("<ButtonRelease-1>", self.on_drag_release)
        self.bind("<ButtonPress-2>", self.on_middle_click)
        self.bind("<B2-Motion>", self.on_middle_drag)
        self.bind("<ButtonRelease-2>", self.on_middle_release)
        self.bind_all("<KeyPress-space>", self.on_space_press)
        self.bind_all("<KeyRelease-space>", self.on_space_release)
        self.bind_all(
            "<Delete>",
            self.delete_callback if self.delete_callback is not None else self.on_delete,
        )

    def create_draggable_rectangle(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        offset: Optional[List[int]] = None,
        max_repetitions: int = 20,
        **kwargs: Any,
    ) -> DraggableRectangle:
        """
        Create a draggable rectangle on the canvas.

        Automatically offsets position if overlapping with existing rectangles.

        Args:
            x1: Top-left x coordinate
            y1: Top-left y coordinate
            x2: Bottom-right x coordinate
            y2: Bottom-right y coordinate
            offset: [dx, dy] offset for overlap avoidance (default: [21, 21])
            max_repetitions: Maximum attempts to find non-overlapping position
            **kwargs: Additional arguments for DraggableRectangle

        Returns:
            The created DraggableRectangle instance
        """
        if offset is None:
            offset = [21, 21]

        draggable_rect = DraggableRectangle(self, x1, y1, x2, y2, **kwargs)
        repetitions = 0

        while repetitions < max_repetitions:
            topleft_pos = draggable_rect.get_topleft_pos()
            overlap = False
            overlapping_items = self.find_overlapping(
                topleft_pos[0] - 2, topleft_pos[1] - 2, topleft_pos[0] + 2, topleft_pos[1] + 2
            )

            if overlapping_items:
                for obj in self.objects.values():
                    if obj.rect in overlapping_items:
                        new_pos = [
                            x1 + offset[0] * (repetitions + 1),
                            y1 + offset[1] * (repetitions + 1),
                        ]
                        draggable_rect.set_topleft_pos(new_pos)
                        overlap = True
                        break

            if not overlap:
                break
            repetitions += 1

        self.objects[self.next_item_id] = draggable_rect
        self.next_item_id += 1
        return draggable_rect

    def copy_draggable_rectangle(
        self,
        draggable_rect: DraggableRectangle,
        offset: Optional[List[int]] = None,
        max_repetitions: int = 20,
        **kwargs: Any,
    ) -> DraggableRectangle:
        """
        Create a copy of an existing draggable rectangle.

        Args:
            draggable_rect: Rectangle to copy
            offset: [dx, dy] offset for the copy (default: [21, 21])
            max_repetitions: Maximum attempts to find non-overlapping position
            **kwargs: Override arguments for the copy

        Returns:
            The copied DraggableRectangle instance
        """
        if offset is None:
            offset = [21, 21]

        new_draggable_rect = draggable_rect.copy_(**kwargs)
        repetitions = 0

        while repetitions < max_repetitions:
            topleft_pos = new_draggable_rect.get_topleft_pos()
            overlap = False
            overlapping_items = self.find_overlapping(
                topleft_pos[0] - 2, topleft_pos[1] - 2, topleft_pos[0] + 2, topleft_pos[1] + 2
            )

            if overlapping_items:
                for obj in self.objects.values():
                    if obj.rect in overlapping_items:
                        new_pos = [
                            topleft_pos[0] + offset[0] * (repetitions + 1),
                            topleft_pos[1] + offset[1] * (repetitions + 1),
                        ]
                        new_draggable_rect.set_topleft_pos(new_pos)
                        overlap = True
                        break

            if not overlap:
                break
            repetitions += 1

        self.objects[self.next_item_id] = new_draggable_rect
        self.next_item_id += 1
        return new_draggable_rect

    def delete_draggable_rectangle(self, item_id: int) -> None:
        """
        Delete a draggable rectangle by its ID.

        Args:
            item_id: The ID of the rectangle to delete
        """
        if item_id in self.objects:
            obj = self.objects[item_id]
            obj.delete()
            del self.objects[item_id]
            if item_id in self.selected_objects:
                del self.selected_objects[item_id]
            self.deselect_callback()

    def get_selected(self) -> List[DraggableRectangle]:
        """
        Get list of currently selected rectangles.

        Returns:
            List of selected DraggableRectangle instances
        """
        return list(self.selected_objects.values())

    def get_draggable_rectangle(self, item_id: int) -> Optional[DraggableRectangle]:
        """
        Get a draggable rectangle by its ID.

        Args:
            item_id: The ID of the rectangle

        Returns:
            The DraggableRectangle instance or None if not found
        """
        return self.objects.get(item_id)

    def get_item_id(self, draggable_rect: DraggableRectangle) -> Optional[int]:
        """
        Get the ID of a draggable rectangle.

        Args:
            draggable_rect: The rectangle to find

        Returns:
            The item ID or None if not found
        """
        return self._get_key_by_value(self.objects, draggable_rect)

    def on_click(self, event: Event) -> None:
        """Handle left mouse button click."""
        if self.panning:
            self.scan_mark(event.x, event.y)
            return

        shift_pressed = (int(event.state) & 0x0001) != 0
        ctrl_pressed = (int(event.state) & 0x0004) != 0
        canvas_x = self.canvasx(event.x)
        canvas_y = self.canvasy(event.y)
        clicked_items = self.find_overlapping(canvas_x, canvas_y, canvas_x + 1, canvas_y + 1)

        if clicked_items:
            for item_id, obj in self.objects.items():
                if obj.rect in clicked_items:
                    if shift_pressed and not obj.get_is_selected():
                        self.toggle_selection(item_id)
                    elif not shift_pressed and not obj.get_is_selected():
                        self.deselect_all()
                        self.select_item(item_id)
                    elif ctrl_pressed:
                        self.deselect_all()
                        self.select_item(item_id)
                    else:
                        if len(self.get_selected()) < 1:
                            self.deselect_all()
                            self.select_item(item_id)
                    return

        self.deselect_all()
        self.dragging = True

    def on_drag_select(self, event: Event) -> None:
        """Handle mouse drag for selection rectangle."""
        if self.panning:
            self.scan_dragto(event.x, event.y, gain=1)
            return

        if not self.dragging:
            return

        canvas_x = self.canvasx(event.x)
        canvas_y = self.canvasy(event.y)

        if self.start_x is None and self.start_y is None:
            clicked_items = self.find_overlapping(canvas_x, canvas_y, canvas_x + 1, canvas_y + 1)
            if any(self.objects[obj_id].rect in clicked_items for obj_id in self.objects):
                return  # Don't start drag selection if clicking on an object

            self.start_x, self.start_y = canvas_x, canvas_y
            self.selection_rect = self.create_rectangle(
                self.start_x,
                self.start_y,
                canvas_x,
                canvas_y,
                outline="black",
                dash=(2, 2),
                fill="",
            )
        else:
            self.coords(self.selection_rect, self.start_x, self.start_y, canvas_x, canvas_y)
            if self.start_x is not None and self.start_y is not None:
                self.update_selection_area(self.start_x, self.start_y, canvas_x, canvas_y)

    def on_drag_release(self, event: Event) -> None:
        """Handle mouse button release after dragging."""
        self.dragging = False
        if self.selection_rect:
            self.delete(self.selection_rect)
            self.selection_rect = None
        self.start_x, self.start_y = None, None

    def on_middle_click(self, event: Event) -> None:
        """Handle middle mouse button press."""
        self.scan_mark(event.x, event.y)

    def on_middle_drag(self, event: Event) -> None:
        """Handle middle mouse button drag."""
        self.scan_dragto(event.x, event.y, gain=1)

    def on_middle_release(self, event: Event) -> None:
        """Handle middle mouse button release."""

    def on_space_press(self, event: Event) -> None:
        """Handle spacebar press to enable panning mode."""
        self.panning = True

    def on_space_release(self, event: Event) -> None:
        """Handle spacebar release to disable panning mode."""
        self.panning = False

    def on_delete(self, event: Event) -> None:
        """
        Handle Delete key press to remove selected rectangles.

        Args:
            event: The key event
        """
        selected_items = list(self.selected_objects.keys())
        for item_id in selected_items:
            self.delete_draggable_rectangle(item_id)

    def update_selection_area(self, x0: float, y0: float, x1: float, y1: float) -> None:
        """
        Update selection based on drag rectangle.

        Args:
            x0: Top-left x of selection rectangle
            y0: Top-left y of selection rectangle
            x1: Bottom-right x of selection rectangle
            y1: Bottom-right y of selection rectangle
        """
        selected = self.find_enclosed(x0, y0, x1, y1)
        for item_id, obj in self.objects.items():
            if obj.rect in selected and not obj.get_is_selected():
                self.select_item(item_id)
            elif obj.rect not in selected and obj.get_is_selected():
                self.deselect_item(item_id)

    def toggle_selection(self, item_id: int) -> None:
        """
        Toggle selection state of a rectangle.

        Args:
            item_id: The ID of the rectangle to toggle
        """
        if self.objects[item_id].get_is_selected():
            self.deselect_item(item_id)
        else:
            self.select_item(item_id)

    def select_item(self, item_id: int) -> None:
        """
        Select a rectangle.

        Args:
            item_id: The ID of the rectangle to select
        """
        obj = self.objects[item_id]
        obj.set_is_selected(True)
        self.itemconfig(obj.rect, outline=self.select_outline_color)
        self.selected_objects[item_id] = obj
        self.select_callback()

    def select_all(self) -> None:
        """Select all rectangles on the canvas."""
        for item_id in self.objects:
            self.select_item(item_id)

    def deselect_item(self, item_id: int) -> None:
        """
        Deselect a rectangle.

        Args:
            item_id: The ID of the rectangle to deselect
        """
        obj = self.objects[item_id]
        obj.set_is_selected(False)
        self.itemconfig(obj.rect, outline=obj.original_outline)
        if item_id in self.selected_objects:
            del self.selected_objects[item_id]
        self.deselect_callback()

    def deselect_all(self) -> None:
        """Deselect all currently selected rectangles."""
        for item_id in list(self.selected_objects):
            self.deselect_item(item_id)

    @staticmethod
    def _get_key_by_value(dictionary: Dict[Any, Any], value: Any) -> Optional[Any]:
        """
        Find the first key corresponding to a value in a dictionary.

        Args:
            dictionary: The dictionary to search
            value: The value to find

        Returns:
            The corresponding key, or None if not found
        """
        for key, val in dictionary.items():
            if val == value:
                return key
        return None
