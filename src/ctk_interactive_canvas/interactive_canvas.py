"""
Interactive Canvas Widget for CustomTkinter

Provides a canvas with built-in support for draggable rectangles, multi-selection,
drag-to-select, panning, and keyboard shortcuts.

Author: Tchicdje Kouojip Joram Smith (DeltaGa)
Created: Tue Aug 6, 2024
"""

from tkinter import Event, Canvas as TkCanvas
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
        enable_history: bool = True,
        enable_zoom: bool = True,
        **kwargs: Any,
    ) -> None:
        """
        Initialize an InteractiveCanvas.

        Args:
            master: Parent widget
            select_callback: Called when objects are selected
            deselect_callback: Called when objects are deselected
            delete_callback: Called when Delete key is pressed (overrides default).
                             May accept zero or one (event) argument.
            select_outline_color: Color for selected object outlines
            dpi: Dots per inch for coordinate conversions
            create_bindings: Whether to create default mouse/keyboard bindings
            enable_history: Enable undo/redo functionality (default: True)
            enable_zoom: Enable zoom functionality (default: True)
            **kwargs: Additional arguments passed to CTkCanvas
        """
        super().__init__(master, **kwargs)

        self.select_callback = select_callback if select_callback is not None else lambda: None
        self.deselect_callback = (
            deselect_callback if deselect_callback is not None else lambda: None
        )
        # Store the raw user-provided delete callback (may be None).
        # We always bind <Delete> to our own _on_delete_key handler,
        # which dispatches to this callback or the default on_delete.
        self._user_delete_callback = delete_callback

        self.select_outline_color = select_outline_color
        self.selected_objects: Dict[int, DraggableRectangle] = {}
        self.objects: Dict[int, DraggableRectangle] = {}
        self.dpi = dpi

        self.start_x: Optional[float] = None
        self.start_y: Optional[float] = None
        self.selection_rect: Optional[int] = None
        self.dragging: bool = False
        self.panning: bool = False

        self.next_item_id: int = 0

        # Internal flags
        self._suppress_registration: bool = False
        self._restoring_state: bool = False
        self._objects_changed: bool = False

        self.enable_history = enable_history
        self.enable_zoom = enable_zoom

        if self.enable_history:
            self.history_states: List[Dict] = []
            self.history_index: int = -1
            self.max_history: int = 50
            # Save the initial empty state so undo can return to empty canvas
            self._save_initial_state()

        if self.enable_zoom:
            self.zoom_level: float = 1.0
            self.min_zoom: float = 0.1
            self.max_zoom: float = 10.0
            self._tracked_images: Dict[int, Dict] = {}

        if create_bindings:
            self._create_bindings()

    def _save_initial_state(self) -> None:
        """Save the initial empty state as history index 0."""
        self.history_states = [{"objects": {}, "next_item_id": 0, "selected": []}]
        self.history_index = 0

    def get_view_center(self) -> List[float]:
        """
        Get the center of the currently visible canvas area.

        Accounts for panning and scrolling by converting widget-space
        coordinates to canvas-space via canvasx/canvasy.

        Returns:
            [x, y] canvas coordinates of the visible center.
        """
        canvas_width = self.winfo_width() if self.winfo_width() > 1 else self.winfo_reqwidth()
        canvas_height = self.winfo_height() if self.winfo_height() > 1 else self.winfo_reqheight()
        return [self.canvasx(canvas_width / 2), self.canvasy(canvas_height / 2)]

    def get_origin_pos(self, reference_item: int) -> List[float]:
        """
        Get the top-left position of a reference canvas item (e.g. a page boundary).

        This mirrors the pattern used in format_editor._canvas_get_origin_pos()
        and is intended to be used as the relative_pos argument for
        DraggableRectangle position methods.

        Args:
            reference_item: Canvas item ID of the reference rectangle.

        Returns:
            [x, y] canvas coordinates of the item's top-left corner.
        """
        coords = self.coords(reference_item)
        return [coords[0], coords[1]]

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

        # Always bind Delete to our internal handler, which properly
        # dispatches to the user's callback (handling event-arg mismatch)
        # or to the default on_delete.
        self.bind_all("<Delete>", self._on_delete_key)

        if self.enable_history:
            self.bind_all("<Control-z>", lambda e: self.undo())
            self.bind_all("<Control-Z>", lambda e: self.undo())
            self.bind_all("<Control-y>", lambda e: self.redo())
            self.bind_all("<Control-Y>", lambda e: self.redo())
            self.bind_all("<Control-Shift-z>", lambda e: self.redo())
            self.bind_all("<Control-Shift-Z>", lambda e: self.redo())

        if self.enable_zoom:
            self.bind_all("<plus>", lambda e: self.zoom_in())
            self.bind_all("<equal>", lambda e: self.zoom_in())
            self.bind_all("<minus>", lambda e: self.zoom_out())
            self.bind("<Alt-MouseWheel>", self.on_zoom_wheel)
            self.bind("<Alt-Button-4>", lambda e: self.zoom_in())
            self.bind("<Alt-Button-5>", lambda e: self.zoom_out())

    def _register_rectangle(self, rect: DraggableRectangle) -> None:
        """
        Register a DraggableRectangle with the canvas.

        Called automatically when a DraggableRectangle is instantiated.
        Ensures all rectangles (including those created via magic methods) are tracked.

        During state restoration, auto-registration is suppressed because
        objects are manually inserted with their original IDs.

        Args:
            rect: The DraggableRectangle instance to register
        """
        if self._suppress_registration:
            return
        if rect not in self.objects.values():
            self.objects[self.next_item_id] = rect
            self.next_item_id += 1

    def coords(self, tag_or_id: Any, *args: Any) -> Any:
        if type(tag_or_id) == str and "ctk_aa_circle_font_element" in self.gettags(tag_or_id):
            coords_id = self.find_withtag(tag_or_id)[0]
            coords = TkCanvas.coords(self, coords_id, *args[:2])
            if len(args) == 3:
                TkCanvas.itemconfigure(
                    self,
                    coords_id,
                    font=("CustomTkinter_shapes_font", -int(args[2]) * 2),
                    text=self._get_char_from_radius(args[2]),
                )
        elif type(tag_or_id) == int and tag_or_id in self._aa_circle_canvas_ids:
            coords = TkCanvas.coords(self, tag_or_id, *args[:2])

            if len(args) == 3:
                TkCanvas.itemconfigure(
                    self,
                    tag_or_id,
                    font=("CustomTkinter_shapes_font", -args[2] * 2),
                    text=self._get_char_from_radius(args[2]),
                )
        else:
            coords = TkCanvas.coords(self, tag_or_id, *args)
            if not coords:
                return [0, 0, 0, 0]
        return coords

    def create_draggable_rectangle(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        offset: Optional[List[int]] = None,
        max_repetitions: int = 20,
        center_on_canvas: bool = False,
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
            center_on_canvas: If True, center rectangle on visible canvas area (default: False)
            **kwargs: Additional arguments for DraggableRectangle

        Returns:
            The created DraggableRectangle instance
        """
        if offset is None:
            offset = [21, 21]

        if center_on_canvas:
            canvas_width = self.winfo_width() if self.winfo_width() > 1 else self.winfo_reqwidth()
            canvas_height = (
                self.winfo_height() if self.winfo_height() > 1 else self.winfo_reqheight()
            )

            rect_width = x2 - x1
            rect_height = y2 - y1

            # Use canvasx/canvasy to get the TRUE visible center,
            # accounting for any panning or scrolling that has occurred.
            # Without this, the center is computed in widget space which
            # diverges from canvas space after any pan/scroll operation.
            center_x = self.canvasx(canvas_width / 2)
            center_y = self.canvasy(canvas_height / 2)

            x1 = center_x - rect_width / 2
            y1 = center_y - rect_height / 2
            x2 = center_x + rect_width / 2
            y2 = center_y + rect_height / 2

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

        if self.enable_history:
            self.save_state()

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

        if self.enable_history:
            self.save_state()

        return new_draggable_rect

    def delete_draggable_rectangle(self, item_id: int) -> None:
        """
        Delete a draggable rectangle by its ID.

        Cleans up attached items (text labels, etc.), removes from
        tracking dictionaries, and optionally saves history state.

        Args:
            item_id: The ID of the rectangle to delete
        """
        if item_id not in self.objects:
            return

        obj = self.objects[item_id]

        # Clean up attached canvas items (text labels, etc.)
        self._delete_attached_items(obj)

        obj.delete()
        del self.objects[item_id]
        if item_id in self.selected_objects:
            del self.selected_objects[item_id]

        # Only fire user callbacks when not restoring state internally
        if not self._restoring_state:
            self.deselect_callback()

    def _delete_attached_items(self, rect: DraggableRectangle) -> None:
        """
        Remove all canvas items attached to a DraggableRectangle.

        Args:
            rect: The rectangle whose attached items should be deleted.
        """
        if hasattr(rect, "_attached_items"):
            for attached_id in rect._attached_items:
                try:
                    self.delete(attached_id)
                except Exception:
                    pass
            rect._attached_items.clear()

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

    def _on_delete_key(self, event: Event) -> None:
        """
        Internal handler for the Delete key binding.

        Dispatches to the user-provided delete_callback if set,
        handling the event-argument mismatch gracefully. Falls back
        to the default on_delete if no user callback was provided.

        The previous implementation bound directly to the user's callback,
        which crashed because:
        - tkinter always passes an Event to key bindings
        - User callbacks may not accept an event argument (e.g. lambda: None)
        - The fallback path was unreachable due to a truthy-check bug

        Args:
            event: The key event from tkinter
        """
        if self._user_delete_callback is not None:
            try:
                # Try calling with event (proper tkinter callback signature)
                self._user_delete_callback(event)
            except TypeError:
                # Callback doesn't accept event — call without it
                try:
                    self._user_delete_callback()
                except TypeError:
                    pass
        else:
            self.on_delete(event)

    def on_delete(self, event: Event) -> None:
        """
        Default handler for Delete key: remove all selected rectangles.

        Saves history state after deletion so it can be undone.

        Args:
            event: The key event
        """
        selected_items = list(self.selected_objects.keys())
        if not selected_items:
            return

        for item_id in selected_items:
            self.delete_draggable_rectangle(item_id)

        if self.enable_history:
            self.save_state()

    def _on_objects_changed(self) -> None:
        """
        Called by DraggableRectangle on ButtonRelease after a drag or resize.

        If any actual movement or resize occurred (tracked by the
        _objects_changed flag set during on_drag/on_resize_drag),
        saves the current state to history for undo/redo support.
        """
        if self._objects_changed and self.enable_history:
            self.save_state()
        self._objects_changed = False

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

    def save_state(self) -> None:
        """
        Save current canvas state to history for undo/redo.

        Captures full visual properties of every DraggableRectangle:
        coordinates, DPI, outline color, fill color, line width, handle
        radius, and current selection state. This ensures that undo/redo
        correctly restores the complete visual appearance.

        This method is called automatically on:
        - Rectangle creation (create_draggable_rectangle)
        - Rectangle deletion (on_delete)
        - Move end (ButtonRelease after drag)
        - Resize end (ButtonRelease after handle drag)
        - Copy (copy_draggable_rectangle)

        For operations managed by the application layer (e.g. align,
        distribute, rotate), call save_state() explicitly after the
        operation completes.
        """
        if not self.enable_history:
            return

        state: Dict = {
            "objects": {},
            "next_item_id": self.next_item_id,
            "selected": list(self.selected_objects.keys()),
        }

        for item_id, obj in self.objects.items():
            coords = list(obj)
            state["objects"][item_id] = {
                "coords": coords,
                "dpi": obj.dpi,
                "outline": obj.original_outline,
                "fill": obj.fill_color,
                "line_width": obj.line_width,
                "handle_radius": obj.handle_radius,
            }

        # Truncate any future states if we're in the middle of the history
        if self.history_index < len(self.history_states) - 1:
            self.history_states = self.history_states[: self.history_index + 1]

        self.history_states.append(state)

        # Cap history at max_history, shifting the window forward
        if len(self.history_states) > self.max_history:
            self.history_states.pop(0)
        else:
            self.history_index += 1

    def undo(self) -> None:
        """
        Undo the last operation.

        Restores the canvas to the previous state in the history stack.
        The initial empty-canvas state at index 0 is reachable, so
        undoing all operations returns to a blank canvas.
        """
        if not self.enable_history:
            return

        if self.history_index > 0:
            self.history_index -= 1
            self._restore_state(self.history_states[self.history_index])

    def redo(self) -> None:
        """
        Redo the previously undone operation.

        Moves forward in the history stack if a future state exists.
        """
        if not self.enable_history:
            return

        if self.history_index < len(self.history_states) - 1:
            self.history_index += 1
            self._restore_state(self.history_states[self.history_index])

    def _restore_state(self, state: Dict) -> None:
        """
        Restore canvas to a saved state.

        This is a full canvas rebuild:
        1. Deletes all current DraggableRectangles (suppressing user callbacks)
        2. Recreates rectangles from the saved state (suppressing auto-registration)
        3. Restores selection state

        Flags _restoring_state and _suppress_registration prevent
        side effects during the rebuild (no deselect callbacks, no
        ID counter conflicts from auto-registration).

        Args:
            state: A history state dictionary from save_state().
        """
        self._restoring_state = True
        self._suppress_registration = True

        try:
            # 1. Remove all current objects without triggering user callbacks
            for item_id in list(self.objects.keys()):
                self.delete_draggable_rectangle(item_id)

            self.objects.clear()
            self.selected_objects.clear()

            # 2. Restore next_item_id BEFORE creating rects
            self.next_item_id = state["next_item_id"]

            # 3. Recreate each rectangle with full visual properties
            for item_id_key, obj_data in state["objects"].items():
                item_id = int(item_id_key) if isinstance(item_id_key, str) else item_id_key
                coords = obj_data["coords"]

                rect = DraggableRectangle(
                    self,
                    coords[0],
                    coords[1],
                    coords[2],
                    coords[3],
                    dpi=obj_data.get("dpi", self.dpi),
                    outline=obj_data.get("outline", "black"),
                    fill=obj_data.get("fill", ""),
                    width=obj_data.get("line_width", 5),
                    radius=obj_data.get("handle_radius", 5),
                )
                self.objects[item_id] = rect

            # 4. Restore selection
            saved_selected = state.get("selected", [])
            for item_id in saved_selected:
                if item_id in self.objects:
                    self.select_item(item_id)

        finally:
            self._suppress_registration = False
            self._restoring_state = False

    def track_image(
        self,
        image_id: int,
        original_image: Any,
        anchor: str = "center",
    ) -> None:
        """
        Register a canvas image item for automatic rescaling during zoom.

        Tkinter's canvas.scale() does NOT resize images — it only moves their
        anchor point. This method tracks the image so that zoom_in/zoom_out
        can perform proper PIL-based resizing.

        Args:
            image_id: The canvas item ID returned by create_image().
            original_image: The original PIL.Image.Image (NOT ImageTk).
            anchor: The anchor used when the image was placed (default: "center").
        """
        if not self.enable_zoom:
            return

        self._tracked_images[image_id] = {
            "original": original_image,
            "anchor": anchor,
            "tk_ref": None,
        }
        self._rescale_tracked_image(image_id)

    def untrack_image(self, image_id: int) -> None:
        """
        Stop tracking a canvas image for zoom rescaling.

        Args:
            image_id: The canvas item ID to stop tracking.
        """
        self._tracked_images.pop(image_id, None)

    def _rescale_tracked_image(self, image_id: int) -> None:
        """Rescale a single tracked image to the current zoom level."""
        try:
            from PIL import Image as PILImage, ImageTk
        except ImportError:
            return

        info = self._tracked_images.get(image_id)
        if info is None:
            return

        original = info["original"]
        new_width = max(1, int(original.width * self.zoom_level))
        new_height = max(1, int(original.height * self.zoom_level))

        resized = original.resize((new_width, new_height), PILImage.LANCZOS)
        tk_image = ImageTk.PhotoImage(resized)

        # Keep a strong reference so tkinter doesn't garbage-collect it
        info["tk_ref"] = tk_image
        self.itemconfigure(image_id, image=tk_image)

    def _rescale_all_tracked_images(self) -> None:
        """Rescale every tracked image to the current zoom level."""
        dead_ids = []
        for image_id in list(self._tracked_images):
            try:
                self._rescale_tracked_image(image_id)
            except Exception:
                dead_ids.append(image_id)

        for dead_id in dead_ids:
            self._tracked_images.pop(dead_id, None)

    def zoom_in(self, factor: float = 1.2) -> None:
        """
        Zoom in on the canvas, centered on the current view.

        Scales all canvas items (rectangles, lines, text) via the native
        canvas.scale() call, then performs PIL-based resizing on any
        tracked images since canvas.scale() does not resize bitmaps.

        Args:
            factor: Zoom multiplier (default: 1.2)
        """
        if not self.enable_zoom:
            return

        new_zoom = self.zoom_level * factor
        if new_zoom <= self.max_zoom:
            # Zoom from the visible center so the viewport stays anchored
            cx, cy = self.get_view_center()
            self.zoom_level = new_zoom
            self.scale("all", cx, cy, factor, factor)
            self._rescale_all_tracked_images()

    def zoom_out(self, factor: float = 1.2) -> None:
        """
        Zoom out on the canvas, centered on the current view.

        Args:
            factor: Zoom divisor (default: 1.2)
        """
        if not self.enable_zoom:
            return

        new_zoom = self.zoom_level / factor
        if new_zoom >= self.min_zoom:
            cx, cy = self.get_view_center()
            self.zoom_level = new_zoom
            self.scale("all", cx, cy, 1 / factor, 1 / factor)
            self._rescale_all_tracked_images()

    def on_zoom_wheel(self, event: Event) -> None:
        """Handle Alt+MouseWheel zoom."""
        if not self.enable_zoom:
            return

        if event.delta > 0:
            self.zoom_in(1.1)
        else:
            self.zoom_out(1.1)

    def attach_text_to_rectangle(self, text_id: int, rect: DraggableRectangle) -> None:
        """
        Attach a text item to a rectangle so they move together.

        Args:
            text_id: Canvas text item ID
            rect: DraggableRectangle to attach text to
        """
        if not hasattr(rect, "_attached_items"):
            rect._attached_items = []
        rect._attached_items.append(text_id)

    def move_attached_items(self, rect: DraggableRectangle, dx: float, dy: float) -> None:
        """
        Move items attached to a rectangle.

        Args:
            rect: Rectangle whose attached items should move
            dx: X displacement
            dy: Y displacement
        """
        if hasattr(rect, "_attached_items"):
            for item_id in rect._attached_items:
                try:
                    self.move(item_id, dx, dy)
                except:
                    pass
