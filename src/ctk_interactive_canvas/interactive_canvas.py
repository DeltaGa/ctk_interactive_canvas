"""
Interactive Canvas Widget for CustomTkinter

Provides a canvas with built-in support for draggable rectangles, multi-selection,
drag-to-select, panning, and keyboard shortcuts.

Author: Tchicdje Kouojip Joram Smith (DeltaGa)
Created: Tue Aug 6, 2024
"""

import contextlib
from collections.abc import Callable
from tkinter import Canvas as TkCanvas
from tkinter import Event
from typing import Any, Dict, FrozenSet, List, Optional, Set, Tuple, Union, cast

import customtkinter as ctk

from ._bindings import CanvasBindings
from ._grid import CanvasGrid
from .draggable_rectangle import DraggableRectangle


class InteractiveCanvas(ctk.CTkCanvas):
    """
    Extended CTkCanvas with interactive selection and manipulation features.

    Supports:
    - Multi-selection (shift-click, drag-select)
    - Panning (middle mouse or space + drag)
    - Keyboard shortcuts (Delete key)
    - Callbacks for selection events
    - Dynamic callback system via register_callback() / unregister_callback()

    Dynamic Callback System
    -----------------------
    Every public interaction method is a hookable point.  Use
    ``register_callback(hook_name, fn, mode)`` to intercept it:

    * mode="before"   — fires *before* the built-in logic
    * mode="after"    — fires *after* the built-in logic (default)
    * mode="inplace"  — *replaces* the built-in logic entirely

    Rectangle-level hooks (``rect_on_*``) receive the originating
    ``DraggableRectangle`` as their first argument, followed by the
    original event arguments.

    Performance: the registry is a plain ``dict``.  When no callbacks are
    registered for a hook, ``_dispatch`` short-circuits after a single
    O(1) ``dict.__contains__`` check — zero overhead on hot paths such as
    ``rect_on_drag`` / ``rect_on_resize_drag`` (~60 Hz).

    All valid hook names are listed in ``InteractiveCanvas._HOOKABLE_METHODS``.
    """

    _HOOKABLE_METHODS: FrozenSet[str] = frozenset(
        {
            # Canvas-level hooks
            "on_click",
            "on_drag_select",
            "on_drag_release",
            "on_middle_click",
            "on_middle_drag",
            "on_middle_release",
            "on_space_press",
            "on_space_release",
            "on_delete",
            "update_selection_area",
            "toggle_selection",
            "select_item",
            "select_all",
            "deselect_item",
            "deselect_all",
            "create_draggable_rectangle",
            "copy_draggable_rectangle",
            "delete_draggable_rectangle",
            "zoom_in",
            "zoom_out",
            "on_zoom_wheel",
            "attach_text_to_rectangle",
            "move_attached_items",
            "undo",
            "redo",
            "copy",
            "cut",
            "paste",
            "duplicate",
            # Rectangle-level hooks (dispatched via _dispatch_rect)
            "rect_on_click",
            "rect_on_drag",
            "rect_on_drag_end",
            "rect_on_resize_click",
            "rect_on_resize_drag",
            "rect_on_resize_end",
        }
    )

    def __init__(
        self,
        master: Optional[Any] = None,
        select_callback: Optional[Callable[[], None]] = None,
        deselect_callback: Optional[Callable[[], None]] = None,
        delete_callback: Optional[Callable[..., None]] = None,
        select_outline_color: str = "#16fff6",
        dpi: int = 300,
        create_bindings: bool = True,
        enable_history: bool = True,
        enable_zoom: bool = True,
        bindings: Optional[CanvasBindings] = None,
        max_history: int = 50,
        min_zoom: float = 0.1,
        max_zoom: float = 10.0,
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
            bindings: Custom event binding strings.  Pass a ``CanvasBindings``
                instance to remap any keyboard or mouse sequence without
                subclassing.  Defaults to ``CanvasBindings()`` (standard bindings).
            max_history: Maximum number of undo/redo snapshots to retain (default: 50).
                Only used when ``enable_history=True``.
            min_zoom: Minimum allowed zoom level (default: 0.1).
                Only used when ``enable_zoom=True``.
            max_zoom: Maximum allowed zoom level (default: 10.0).
                Only used when ``enable_zoom=True``.
            **kwargs: Additional arguments passed to CTkCanvas
        """
        super().__init__(master, **kwargs)

        # Defensive: ensure _aa_circle_canvas_ids exists for coords() fast path
        # even if CTkCanvas didn't set it (shouldn't happen, but safe).
        if not hasattr(self, "_aa_circle_canvas_ids"):
            self._aa_circle_canvas_ids: Set[int] = set()

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
        # O(1) reverse lookups: id(rect) → item_id, and registered set
        self._rect_to_id: Dict[int, int] = {}
        self._registered_rects: Set[int] = set()
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

        # Dynamic callback registry: {hook_name: {mode: [(callable, suppress_during_restore)]}}
        self._callbacks: Dict[str, Dict[str, List[Tuple[Callable, bool]]]] = {}

        # Clipboard — internal snapshot list for copy/cut/paste/duplicate.
        # Each entry mirrors the save_state() per-object format.
        self._clipboard: List[Dict] = []

        self.enable_history = enable_history
        self.enable_zoom = enable_zoom

        # Binding strings: custom instance or the default set.
        # Stored before _create_bindings() so DraggableRectangle.__init__
        # can read canvas._bindings via getattr.
        self._bindings: CanvasBindings = bindings if bindings is not None else CanvasBindings()

        if self.enable_history:
            self.history_states: List[Dict] = []
            self.history_index: int = -1
            self.max_history: int = max_history
            # Save the initial empty state so undo can return to empty canvas
            self._save_initial_state()

        # Always initialize zoom attributes so _canvas_to_logical_coords /
        # _logical_to_canvas_coords can use direct attribute access (no getattr
        # fallback). When zoom is disabled these stay at identity values.
        self.zoom_level: float = 1.0
        self._canvas_origin_x: float = 0.0
        self._canvas_origin_y: float = 0.0

        if self.enable_zoom:
            self.min_zoom: float = min_zoom
            self.max_zoom: float = max_zoom
            self._tracked_images: Dict[int, Dict] = {}

        if create_bindings:
            self._create_bindings()

    # -------------------------------------------------------------------------
    # Callback registry
    # -------------------------------------------------------------------------

    def register_callback(
        self,
        hook_name: str,
        callback: Callable,
        mode: str = "after",
        suppress_during_restore: bool = False,
    ) -> None:
        """
        Register a callback for a hookable method.

        Args:
            hook_name: Name of the hook (must be in ``_HOOKABLE_METHODS``).
            callback: Callable to invoke.  Rectangle-level hooks (``rect_on_*``)
                receive the ``DraggableRectangle`` as their first argument.
            mode: One of:
                * ``"before"``        — called *before* the built-in logic.
                * ``"after"``         — called *after* the built-in logic (default).
                * ``"inplace"``       — *replaces* the built-in logic entirely.
                  Only the first registered inplace callback is used.
                * ``"after_result"``  — called *after* the built-in logic with
                  ``result`` prepended as the first positional argument.  Use
                  this mode when you need the operation's return value —
                  e.g. the newly created ``DraggableRectangle`` list from
                  ``paste`` / ``duplicate`` / ``copy``, the deleted rect from
                  ``delete_draggable_rectangle``, or the created rect from
                  ``create_draggable_rectangle``.  Signature::

                      def on_paste(result, *args, **kwargs): ...
                      canvas.register_callback("paste", on_paste, mode="after_result")

            suppress_during_restore: If ``True``, this callback is silenced
                while undo/redo state restoration is in progress.

        Raises:
            ValueError: If ``hook_name`` is not a valid hook or ``mode`` is invalid.
        """
        if hook_name not in self._HOOKABLE_METHODS:
            raise ValueError(
                f"Unknown hook: {hook_name!r}. " f"Valid hooks: {sorted(self._HOOKABLE_METHODS)}"
            )
        if mode not in ("before", "after", "inplace", "after_result"):
            raise ValueError(
                f"Invalid mode: {mode!r}. "
                "Must be 'before', 'after', 'inplace', or 'after_result'."
            )
        if hook_name not in self._callbacks:
            self._callbacks[hook_name] = {}
        hook_dict = self._callbacks[hook_name]
        if mode not in hook_dict:
            hook_dict[mode] = []
        hook_dict[mode].append((callback, suppress_during_restore))

    def unregister_callback(
        self,
        hook_name: str,
        callback: Callable,
        mode: str = "after",
    ) -> bool:
        """
        Unregister a previously registered callback.

        When the last callback for a hook is removed, the hook entry is
        deleted from the registry so the zero-overhead fast path is restored.

        Args:
            hook_name: Name of the hook.
            callback: The callable to remove (matched by identity, not equality).
            mode: The mode it was registered under (default: ``"after"``).

        Returns:
            ``True`` if the callback was found and removed, ``False`` otherwise.
        """
        if hook_name not in self._callbacks:
            return False
        hook_dict = self._callbacks[hook_name]
        if mode not in hook_dict:
            return False
        entries = hook_dict[mode]
        for i, (cb, _) in enumerate(entries):
            if cb is callback:
                entries.pop(i)
                if not entries:
                    del hook_dict[mode]
                if not hook_dict:
                    del self._callbacks[hook_name]
                return True
        return False

    def _dispatch(self, hook_name: str, builtin_fn: Callable, *args: Any, **kwargs: Any) -> Any:
        """
        Dispatch a canvas-level hookable method through the callback registry.

        Zero-overhead fast path: when ``hook_name`` has no active callbacks the
        dict lookup short-circuits immediately and ``builtin_fn`` is invoked
        directly, adding no measurable overhead to hot paths.

        Args:
            hook_name: Registry key identifying the hook.
            builtin_fn: Bound built-in implementation (``self._builtin_*``).
            *args: Positional arguments forwarded to callbacks and built-in.
            **kwargs: Keyword arguments forwarded to callbacks and built-in.

        Returns:
            Return value of the built-in (or inplace) function.
        """
        if hook_name not in self._callbacks:
            return builtin_fn(*args, **kwargs)

        hooks = self._callbacks[hook_name]
        restoring = self._restoring_state

        for cb, suppress in hooks.get("before", ()):
            if not (suppress and restoring):
                cb(*args, **kwargs)

        inplace_list = hooks.get("inplace")
        if inplace_list:
            cb, suppress = inplace_list[0]
            result = (
                builtin_fn(*args, **kwargs) if (suppress and restoring) else cb(*args, **kwargs)
            )
        else:
            result = builtin_fn(*args, **kwargs)

        for cb, suppress in hooks.get("after", ()):
            if not (suppress and restoring):
                cb(*args, **kwargs)

        for cb, suppress in hooks.get("after_result", ()):
            if not (suppress and restoring):
                cb(result, *args, **kwargs)

        return result

    def _dispatch_rect(
        self,
        hook_name: str,
        rect: "DraggableRectangle",
        builtin_fn: Callable,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """
        Dispatch a rectangle-level hookable method through the callback registry.

        Identical semantics to ``_dispatch`` but prepends the originating
        ``DraggableRectangle`` instance as the first argument to every callback,
        so callers can identify which rectangle triggered the event.

        Args:
            hook_name: Registry key identifying the hook.
            rect: The DraggableRectangle that originated the event.
            builtin_fn: Bound built-in on the rectangle (``rect._builtin_*``).
            *args: Event arguments forwarded after ``rect``.
            **kwargs: Keyword arguments forwarded.

        Returns:
            Return value of the built-in (or inplace) function.
        """
        if hook_name not in self._callbacks:
            return builtin_fn(*args, **kwargs)

        hooks = self._callbacks[hook_name]
        restoring = self._restoring_state

        for cb, suppress in hooks.get("before", ()):
            if not (suppress and restoring):
                cb(rect, *args, **kwargs)

        inplace_list = hooks.get("inplace")
        if inplace_list:
            cb, suppress = inplace_list[0]
            result = (
                builtin_fn(*args, **kwargs)
                if (suppress and restoring)
                else cb(rect, *args, **kwargs)
            )
        else:
            result = builtin_fn(*args, **kwargs)

        for cb, suppress in hooks.get("after", ()):
            if not (suppress and restoring):
                cb(rect, *args, **kwargs)

        for cb, suppress in hooks.get("after_result", ()):
            if not (suppress and restoring):
                cb(result, rect, *args, **kwargs)

        return result

    # -------------------------------------------------------------------------
    # Internal helpers (not hookable)
    # -------------------------------------------------------------------------

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
        b = self._bindings
        self.bind(b.mouse_left_click, self.on_click)
        self.bind(b.mouse_left_drag, self.on_drag_select)
        self.bind(b.mouse_left_release, self.on_drag_release)
        self.bind(b.mouse_middle_click, self.on_middle_click)
        self.bind(b.mouse_middle_drag, self.on_middle_drag)
        self.bind(b.mouse_middle_release, self.on_middle_release)
        self.bind_all(b.space_press, self.on_space_press)
        self.bind_all(b.space_release, self.on_space_release)

        # Always bind Delete to our internal handler, which properly
        # dispatches to the user's callback (handling event-arg mismatch)
        # or to the default on_delete.
        self.bind_all(b.delete_key, self._on_delete_key)

        if self.enable_history:
            self.bind_all(b.undo, lambda e: self.undo())
            self.bind_all(b.undo_upper, lambda e: self.undo())
            self.bind_all(b.redo_y, lambda e: self.redo())
            self.bind_all(b.redo_y_upper, lambda e: self.redo())
            self.bind_all(b.redo_shift_z, lambda e: self.redo())
            self.bind_all(b.redo_shift_z_upper, lambda e: self.redo())

        if self.enable_zoom:
            self.bind_all(b.zoom_in_plus, lambda e: self.zoom_in())
            self.bind_all(b.zoom_in_equal, lambda e: self.zoom_in())
            self.bind_all(b.zoom_out_minus, lambda e: self.zoom_out())
            self.bind(b.zoom_wheel, self.on_zoom_wheel)
            self.bind(b.zoom_wheel_up, lambda e: self.zoom_in())
            self.bind(b.zoom_wheel_down, lambda e: self.zoom_out())

        self.bind_all(b.copy, lambda e: self.copy())
        self.bind_all(b.copy_upper, lambda e: self.copy())
        self.bind_all(b.cut, lambda e: self.cut())
        self.bind_all(b.cut_upper, lambda e: self.cut())
        self.bind_all(b.paste, lambda e: self.paste())
        self.bind_all(b.paste_upper, lambda e: self.paste())
        self.bind_all(b.duplicate, lambda e: self.duplicate())
        self.bind_all(b.duplicate_upper, lambda e: self.duplicate())

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
        rect_id = id(rect)
        if rect_id not in self._registered_rects:
            self._registered_rects.add(rect_id)
            self._rect_to_id[rect_id] = self.next_item_id
            self.objects[self.next_item_id] = rect
            self.next_item_id += 1

    def coords(self, tag_or_id: Any, *args: Any) -> Any:
        # Fast path: most calls are plain int IDs for regular rectangles.
        # Check the common case first to avoid expensive gettags()/isinstance.
        if isinstance(tag_or_id, int):
            if tag_or_id not in self._aa_circle_canvas_ids:
                coords = TkCanvas.coords(self, tag_or_id, *args)
                if not coords:
                    return [0, 0, 0, 0]
                return coords
            # aa_circle by int ID (rare)
            coords = TkCanvas.coords(self, tag_or_id, *args[:2])
            if len(args) == 3:
                TkCanvas.itemconfigure(
                    self,
                    tag_or_id,
                    font=("CustomTkinter_shapes_font", -args[2] * 2),
                    text=self._get_char_from_radius(args[2]),
                )
        elif isinstance(tag_or_id, str) and "ctk_aa_circle_font_element" in self.gettags(tag_or_id):
            coords_id = self.find_withtag(tag_or_id)[0]
            coords = TkCanvas.coords(self, coords_id, *args[:2])
            if len(args) == 3:
                TkCanvas.itemconfigure(
                    self,
                    coords_id,
                    font=("CustomTkinter_shapes_font", -int(args[2]) * 2),
                    text=self._get_char_from_radius(args[2]),
                )
        else:
            coords = TkCanvas.coords(self, tag_or_id, *args)
            if not coords:
                return [0, 0, 0, 0]
        return coords

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

    # -------------------------------------------------------------------------
    # Rectangle creation / copy / deletion
    # -------------------------------------------------------------------------

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
        return cast(
            DraggableRectangle,
            self._dispatch(
                "create_draggable_rectangle",
                self._builtin_create_draggable_rectangle,
                x1,
                y1,
                x2,
                y2,
                offset=offset,
                max_repetitions=max_repetitions,
                center_on_canvas=center_on_canvas,
                **kwargs,
            ),
        )

    def _builtin_create_draggable_rectangle(
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
            center_x = self.canvasx(canvas_width / 2)
            center_y = self.canvasy(canvas_height / 2)

            x1 = center_x - rect_width / 2
            y1 = center_y - rect_height / 2
            x2 = center_x + rect_width / 2
            y2 = center_y + rect_height / 2

        draggable_rect = DraggableRectangle(self, x1, y1, x2, y2, **kwargs)

        # Build a set of existing rect canvas IDs once — O(n) upfront so the
        # inner check per repetition is O(|overlapping_items|) via set intersection.
        existing_rect_ids: Set[int] = {
            obj.rect for obj in self.objects.values() if obj is not draggable_rect
        }
        repetitions = 0

        while repetitions < max_repetitions:
            topleft_pos = draggable_rect.get_topleft_pos()
            overlapping_items = self.find_overlapping(
                topleft_pos[0] - 2, topleft_pos[1] - 2, topleft_pos[0] + 2, topleft_pos[1] + 2
            )

            if not (set(overlapping_items) & existing_rect_ids):
                break

            repetitions += 1
            draggable_rect.set_topleft_pos(
                [x1 + offset[0] * repetitions, y1 + offset[1] * repetitions]
            )

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
        return cast(
            DraggableRectangle,
            self._dispatch(
                "copy_draggable_rectangle",
                self._builtin_copy_draggable_rectangle,
                draggable_rect,
                offset=offset,
                max_repetitions=max_repetitions,
                **kwargs,
            ),
        )

    def _builtin_copy_draggable_rectangle(
        self,
        draggable_rect: DraggableRectangle,
        offset: Optional[List[int]] = None,
        max_repetitions: int = 20,
        **kwargs: Any,
    ) -> DraggableRectangle:
        if offset is None:
            offset = [21, 21]

        new_draggable_rect = draggable_rect.copy_(**kwargs)

        # Exclude the new copy itself from overlap detection.
        existing_rect_ids: Set[int] = {
            obj.rect for obj in self.objects.values() if obj is not new_draggable_rect
        }
        origin = new_draggable_rect.get_topleft_pos()
        repetitions = 0

        while repetitions < max_repetitions:
            topleft_pos = new_draggable_rect.get_topleft_pos()
            overlapping_items = self.find_overlapping(
                topleft_pos[0] - 2, topleft_pos[1] - 2, topleft_pos[0] + 2, topleft_pos[1] + 2
            )

            if not (set(overlapping_items) & existing_rect_ids):
                break

            repetitions += 1
            new_draggable_rect.set_topleft_pos(
                [origin[0] + offset[0] * repetitions, origin[1] + offset[1] * repetitions]
            )

        if self.enable_history:
            self.save_state()

        return new_draggable_rect

    def delete_draggable_rectangle(self, item_id: int) -> Optional["DraggableRectangle"]:
        """
        Delete a draggable rectangle by its ID.

        Cleans up attached items (text labels, etc.), removes from
        tracking dictionaries, and optionally saves history state.

        Returns the deleted ``DraggableRectangle`` object (canvas items already
        removed), or ``None`` if ``item_id`` was not found.  Use an
        ``after_result`` hook to recover the reference::

            canvas.register_callback(
                "delete_draggable_rectangle", fn, mode="after_result"
            )
            # fn(deleted_rect_or_none, item_id)

        Args:
            item_id: The ID of the rectangle to delete
        """
        return cast(
            "DraggableRectangle | None",
            self._dispatch(
                "delete_draggable_rectangle",
                self._builtin_delete_draggable_rectangle,
                item_id,
            ),
        )

    def _builtin_delete_draggable_rectangle(self, item_id: int) -> Optional["DraggableRectangle"]:
        if item_id not in self.objects:
            return None

        obj = self.objects[item_id]

        # Clean up attached canvas items (text labels, etc.)
        self._delete_attached_items(obj)

        # Clean up reverse lookup maps
        rect_id = id(obj)
        self._registered_rects.discard(rect_id)
        self._rect_to_id.pop(rect_id, None)

        obj.delete()
        del self.objects[item_id]
        if item_id in self.selected_objects:
            del self.selected_objects[item_id]

        # Only fire user callbacks when not restoring state internally
        if not self._restoring_state:
            self.deselect_callback()

        return obj

    def _delete_attached_items(self, rect: DraggableRectangle) -> None:
        """
        Remove all canvas items attached to a DraggableRectangle.

        Args:
            rect: The rectangle whose attached items should be deleted.
        """
        for attached_id in rect._attached_items:
            self.delete(attached_id)
        rect._attached_items.clear()

    # -------------------------------------------------------------------------
    # Selection
    # -------------------------------------------------------------------------

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
        return self._rect_to_id.get(id(draggable_rect))

    def update_selection_area(self, x0: float, y0: float, x1: float, y1: float) -> None:
        """
        Update selection based on drag rectangle.

        Args:
            x0: Top-left x of selection rectangle
            y0: Top-left y of selection rectangle
            x1: Bottom-right x of selection rectangle
            y1: Bottom-right y of selection rectangle
        """
        self._dispatch(
            "update_selection_area",
            self._builtin_update_selection_area,
            x0,
            y0,
            x1,
            y1,
        )

    def _builtin_update_selection_area(self, x0: float, y0: float, x1: float, y1: float) -> None:
        selected = set(self.find_enclosed(x0, y0, x1, y1))
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
        self._dispatch("toggle_selection", self._builtin_toggle_selection, item_id)

    def _builtin_toggle_selection(self, item_id: int) -> None:
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
        self._dispatch("select_item", self._builtin_select_item, item_id)

    def _builtin_select_item(self, item_id: int) -> None:
        obj = self.objects[item_id]
        obj.set_is_selected(True)
        self.itemconfig(obj.rect, outline=self.select_outline_color)
        self.selected_objects[item_id] = obj
        self.select_callback()

    def select_all(self) -> None:
        """Select all rectangles on the canvas."""
        self._dispatch("select_all", self._builtin_select_all)

    def _builtin_select_all(self) -> None:
        for item_id in self.objects:
            self.select_item(item_id)

    def deselect_item(self, item_id: int) -> None:
        """
        Deselect a rectangle.

        Args:
            item_id: The ID of the rectangle to deselect
        """
        self._dispatch("deselect_item", self._builtin_deselect_item, item_id)

    def _builtin_deselect_item(self, item_id: int) -> None:
        obj = self.objects[item_id]
        obj.set_is_selected(False)
        self.itemconfig(obj.rect, outline=obj.original_outline)
        if item_id in self.selected_objects:
            del self.selected_objects[item_id]
        self.deselect_callback()

    def deselect_all(self) -> None:
        """Deselect all currently selected rectangles."""
        self._dispatch("deselect_all", self._builtin_deselect_all)

    def _builtin_deselect_all(self) -> None:
        for item_id in list(self.selected_objects):
            self.deselect_item(item_id)

    # -------------------------------------------------------------------------
    # Mouse and keyboard event handlers
    # -------------------------------------------------------------------------

    def on_click(self, event: Event) -> None:
        """Handle left mouse button click."""
        self._dispatch("on_click", self._builtin_on_click, event)

    def _builtin_on_click(self, event: Event) -> None:
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
                    elif not shift_pressed and not obj.get_is_selected() or ctrl_pressed:
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
        self._dispatch("on_drag_select", self._builtin_on_drag_select, event)

    def _builtin_on_drag_select(self, event: Event) -> None:
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
        self._dispatch("on_drag_release", self._builtin_on_drag_release, event)

    def _builtin_on_drag_release(self, event: Event) -> None:
        self.dragging = False
        if self.selection_rect:
            self.delete(self.selection_rect)
            self.selection_rect = None
        self.start_x, self.start_y = None, None

    def on_middle_click(self, event: Event) -> None:
        """Handle middle mouse button press."""
        self._dispatch("on_middle_click", self._builtin_on_middle_click, event)

    def _builtin_on_middle_click(self, event: Event) -> None:
        self.scan_mark(event.x, event.y)

    def on_middle_drag(self, event: Event) -> None:
        """Handle middle mouse button drag."""
        self._dispatch("on_middle_drag", self._builtin_on_middle_drag, event)

    def _builtin_on_middle_drag(self, event: Event) -> None:
        self.scan_dragto(event.x, event.y, gain=1)

    def on_middle_release(self, event: Event) -> None:
        """Handle middle mouse button release."""
        self._dispatch("on_middle_release", self._builtin_on_middle_release, event)

    def _builtin_on_middle_release(self, event: Event) -> None:
        pass

    def on_space_press(self, event: Event) -> None:
        """Handle spacebar press to enable panning mode."""
        self._dispatch("on_space_press", self._builtin_on_space_press, event)

    def _builtin_on_space_press(self, event: Event) -> None:
        self.panning = True

    def on_space_release(self, event: Event) -> None:
        """Handle spacebar release to disable panning mode."""
        self._dispatch("on_space_release", self._builtin_on_space_release, event)

    def _builtin_on_space_release(self, event: Event) -> None:
        self.panning = False

    # -------------------------------------------------------------------------
    # Delete handling (internal dispatcher is not hookable; on_delete is)
    # -------------------------------------------------------------------------

    def _on_delete_key(self, event: Event) -> None:
        """
        Internal handler for the Delete key binding.

        Dispatches to the user-provided delete_callback if set,
        handling the event-argument mismatch gracefully. Falls back
        to the default on_delete if no user callback was provided.

        Args:
            event: The key event from tkinter
        """
        if self._user_delete_callback is not None:
            try:
                self._user_delete_callback(event)
            except TypeError:
                with contextlib.suppress(TypeError):
                    self._user_delete_callback()
        else:
            self.on_delete(event)

    def on_delete(self, event: Event) -> None:
        """
        Default handler for Delete key: remove all selected rectangles.

        Saves history state after deletion so it can be undone.

        Args:
            event: The key event
        """
        self._dispatch("on_delete", self._builtin_on_delete, event)

    def _builtin_on_delete(self, event: Event) -> None:
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

    # -------------------------------------------------------------------------
    # History
    # -------------------------------------------------------------------------

    def save_state(self) -> None:
        """
        Save current canvas state to history for undo/redo.

        Captures full visual properties of every DraggableRectangle:
        coordinates, DPI, outline color, fill color, line width, handle
        radius, current selection state, and attached item metadata.

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

        state: dict = {
            "objects": {},
            "next_item_id": self.next_item_id,
            "selected": list(self.selected_objects.keys()),
        }

        for item_id, obj in self.objects.items():
            state["objects"][item_id] = {
                "coords": self._canvas_to_logical_coords(list(obj)),
                "dpi": obj.dpi,
                "outline": obj.original_outline,
                "fill": obj.fill_color,
                "line_width": obj.line_width,
                "handle_radius": obj.handle_radius,
                # Strong reference keeps the Python object alive in the history
                # stack so that _restore_state can resurrect it in-place instead
                # of creating a new instance (which would break caller references).
                "rect_ref": obj,
                "attached_items": self._snapshot_attached_items(obj),
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
        self._dispatch("undo", self._builtin_undo)

    def _builtin_undo(self) -> None:
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
        self._dispatch("redo", self._builtin_redo)

    def _builtin_redo(self) -> None:
        if not self.enable_history:
            return
        if self.history_index < len(self.history_states) - 1:
            self.history_index += 1
            self._restore_state(self.history_states[self.history_index])

    # -------------------------------------------------------------------------
    # Clipboard — copy / cut / paste / duplicate
    # -------------------------------------------------------------------------

    def copy(self) -> List["DraggableRectangle"]:
        """
        Copy the current selection to the internal clipboard.

        Snapshots all visual properties (geometry, colours, line width, handle
        radius, DPI, attached items) of every selected rectangle in logical
        (zoom=1.0) coordinates so the snapshot is zoom-invariant.

        Returns the source rectangles (same Python objects, not copies).
        Register an ``after_result`` hook to receive them::

            canvas.register_callback("copy", fn, mode="after_result")
            # fn(copied_rects: List[DraggableRectangle])
        """
        return cast(
            "List[DraggableRectangle]",
            self._dispatch("copy", self._builtin_copy),
        )

    def _builtin_copy(self) -> "List[DraggableRectangle]":
        if not self.selected_objects:
            return []
        rects = list(self.selected_objects.values())
        self._clipboard = [
            {
                "coords": self._canvas_to_logical_coords(list(self.coords(obj.rect))),
                "outline": obj.original_outline,
                "fill": obj.fill_color,
                "line_width": obj.line_width,
                "handle_radius": obj.handle_radius,
                "dpi": obj.dpi,
                "attached_items": self._snapshot_attached_items(obj),
            }
            for obj in rects
        ]
        return rects

    def cut(self) -> "List[DraggableRectangle]":
        """
        Cut the current selection: copy to clipboard then delete.

        Saves a history snapshot after deletion so the cut is undoable.

        Returns the removed rectangles (canvas items already deleted; the
        Python objects remain alive via the history stack's ``rect_ref``).
        Register an ``after_result`` hook to receive them::

            canvas.register_callback("cut", fn, mode="after_result")
            # fn(cut_rects: List[DraggableRectangle])
        """
        return cast(
            "List[DraggableRectangle]",
            self._dispatch("cut", self._builtin_cut),
        )

    def _builtin_cut(self) -> "List[DraggableRectangle]":
        if not self.selected_objects:
            return []
        rects = self._builtin_copy()
        for item_id in list(self.selected_objects):
            self.delete_draggable_rectangle(item_id)
        if self.enable_history:
            self.save_state()
        return rects

    def paste(self) -> "List[DraggableRectangle]":
        """
        Paste clipboard contents, **centered on the current view**.

        Unlike ``duplicate()``, paste always moves the new elements so their
        collective bounding-box center coincides with the visible canvas center,
        regardless of where the originals were.  This mirrors the behaviour of
        Adobe Illustrator's Ctrl+V.

        The previous selection is cleared; pasted rectangles are selected
        automatically.  A history snapshot is saved.

        Returns the newly created rectangles.
        Register an ``after_result`` hook to receive them::

            canvas.register_callback("paste", fn, mode="after_result")
            # fn(pasted_rects: List[DraggableRectangle])
        """
        return cast(
            "List[DraggableRectangle]",
            self._dispatch("paste", self._builtin_paste),
        )

    def _builtin_paste(self) -> "List[DraggableRectangle]":
        if not self._clipboard:
            return []
        return self._paste_impl(center_on_view=True)

    def duplicate(self) -> "List[DraggableRectangle]":
        """
        Duplicate the current selection in-place (Ctrl+D).

        Unlike ``paste()``, duplicate starts each new element at the same
        position as its source.  Overlap avoidance then shifts the group
        incrementally (21 px steps) until no top-left corner collides with an
        existing rectangle, up to 20 attempts.  The originals remain unchanged;
        duplicates are selected automatically.  A history snapshot is saved.

        Returns the newly created rectangles.
        Register an ``after_result`` hook to receive them::

            canvas.register_callback("duplicate", fn, mode="after_result")
            # fn(duplicated_rects: List[DraggableRectangle])
        """
        return cast(
            "List[DraggableRectangle]",
            self._dispatch("duplicate", self._builtin_duplicate),
        )

    def _builtin_duplicate(self) -> "List[DraggableRectangle]":
        if not self.selected_objects:
            return []
        self._builtin_copy()
        return self._paste_impl(center_on_view=False)

    # Overlap avoidance constants used by _paste_impl (match _builtin_create defaults).
    _PASTE_OVERLAP_OFFSET: Tuple[int, int] = (21, 21)
    _PASTE_MAX_REPETITIONS: int = 20

    def _paste_impl(self, center_on_view: bool = True) -> "List[DraggableRectangle]":
        """
        Shared placement engine for paste() and duplicate().

        paste (center_on_view=True):
            Shifts the whole clipboard group so its bounding-box center lands
            on the visible view center, then runs group-based overlap avoidance.

        duplicate (center_on_view=False):
            Places each new rect at the source position (dx=dy=0), then runs
            group-based overlap avoidance.

        Overlap avoidance moves the *entire* group together in 21 px steps so
        the relative layout of a multi-rect clipboard is always preserved.
        Up to ``_PASTE_MAX_REPETITIONS`` attempts are made; if all are
        exhausted the final position is kept regardless.

        Returns:
            Newly created DraggableRectangle instances, already selected.
        """
        if not self._clipboard:
            return []

        if center_on_view:
            all_coords = [data["coords"] for data in self._clipboard]
            min_lx = min(c[0] for c in all_coords)
            min_ly = min(c[1] for c in all_coords)
            max_lx = max(c[2] for c in all_coords)
            max_ly = max(c[3] for c in all_coords)
            clip_cx = (min_lx + max_lx) / 2.0
            clip_cy = (min_ly + max_ly) / 2.0
            # get_view_center() returns canvas-space; convert to logical space
            view_logical = self._canvas_to_logical_coords(self.get_view_center())
            dx = view_logical[0] - clip_cx
            dy = view_logical[1] - clip_cy
        else:
            dx = 0.0
            dy = 0.0

        self._builtin_deselect_all()
        new_rects: List[DraggableRectangle] = []

        for data in self._clipboard:
            logical = data["coords"]
            pasted_logical = [
                logical[0] + dx,
                logical[1] + dy,
                logical[2] + dx,
                logical[3] + dy,
            ]
            canvas_coords = self._logical_to_canvas_coords(pasted_logical)
            rect = DraggableRectangle(
                self,
                canvas_coords[0],
                canvas_coords[1],
                canvas_coords[2],
                canvas_coords[3],
                outline=data["outline"],
                fill=data["fill"],
                width=data["line_width"],
                radius=data["handle_radius"],
                dpi=data["dpi"],
            )
            for snapshot in data["attached_items"]:
                snap_logical = snapshot["coords"]
                pasted_snap_logical = [
                    c + (dx if i % 2 == 0 else dy) for i, c in enumerate(snap_logical)
                ]
                canvas_snapshot = {
                    **snapshot,
                    "coords": self._logical_to_canvas_coords(pasted_snap_logical),
                }
                new_id = self._recreate_attached_item(canvas_snapshot)
                if new_id is not None:
                    rect._attached_items.append(new_id)
            new_rects.append(rect)

        # Group-based overlap avoidance: move all new rects together so their
        # relative layout is preserved.  Only check against pre-existing rects.
        new_rect_ids: Set[int] = {r.rect for r in new_rects}
        existing_rect_ids: Set[int] = {
            obj.rect for obj in self.objects.values() if obj.rect not in new_rect_ids
        }
        off_x, off_y = self._PASTE_OVERLAP_OFFSET

        for _rep in range(self._PASTE_MAX_REPETITIONS):
            collision = False
            for r in new_rects:
                tl = r.get_topleft_pos()
                overlapping = self.find_overlapping(tl[0] - 2, tl[1] - 2, tl[0] + 2, tl[1] + 2)
                if set(overlapping) & existing_rect_ids:
                    collision = True
                    break
            if not collision:
                break
            # Shift the whole group by one offset step (cumulative across iterations)
            for r in new_rects:
                tl = r.get_topleft_pos()
                r.set_topleft_pos([tl[0] + off_x, tl[1] + off_y])

        for r in new_rects:
            self.select_item(self._rect_to_id[id(r)])

        if self.enable_history:
            self.save_state()

        return new_rects

    def _update_rect_in_place(self, rect: "DraggableRectangle", data: dict) -> None:
        """
        Mutate an existing DraggableRectangle to match a saved state snapshot.

        Updates the underlying canvas item geometry and appearance without
        destroying or recreating the Python object, so all external references
        to this rectangle remain valid after an undo/redo operation.

        Attached items are restored via full reconciliation (delete + recreate
        from snapshot), which handles all cases correctly — items added, removed,
        or repositioned between states.  Falls back to dx/dy movement for
        history states saved before attached-item snapshots were introduced.

        Args:
            rect: The live DraggableRectangle instance to update.
            data: A single object entry from a history state dictionary.
        """
        # Saved coords are in logical (zoom=1.0) space; scale to current canvas space.
        coords = self._logical_to_canvas_coords(data["coords"])
        outline = data.get("outline", "black")
        fill = data.get("fill", "")
        line_width = data.get("line_width", 5)
        dpi = data.get("dpi", self.dpi)

        saved_attached = data.get("attached_items")
        if saved_attached is None:
            # Backward compat: compute delta before updating geometry
            old_coords = self.coords(rect.rect)
            dx = coords[0] - old_coords[0]
            dy = coords[1] - old_coords[1]
        else:
            # Full reconciliation: delete current attached items first
            for attached_id in rect._attached_items:
                self.delete(attached_id)
            rect._attached_items.clear()

        # Update geometry of both canvas items
        self.coords(rect.rect, coords[0], coords[1], coords[2], coords[3])
        self.coords(rect.resize_handle, coords[2], coords[3])

        # Restore attached items
        if saved_attached is not None:
            for snapshot in saved_attached:
                # Attached item coords are also in logical space; scale back.
                canvas_snapshot = {
                    **snapshot,
                    "coords": self._logical_to_canvas_coords(snapshot["coords"]),
                }
                new_id = self._recreate_attached_item(canvas_snapshot)
                if new_id is not None:
                    rect._attached_items.append(new_id)
        elif dx or dy:
            # Backward compat fallback: move existing attached items by delta
            self.move_attached_items(rect, dx, dy)

        # Update visual appearance on the canvas
        self.itemconfig(rect.rect, outline=outline, fill=fill, width=line_width)

        # Sync Python-side state attributes
        rect.original_outline = outline
        rect.fill_color = fill
        rect.line_width = line_width
        rect.dpi = dpi

    def _resurrect_rect(self, rect: "DraggableRectangle", data: dict) -> None:
        """
        Re-attach a previously deleted DraggableRectangle back onto the canvas.

        When a rectangle is removed during undo (surplus step), its Python object
        is kept alive inside the history snapshot via the ``rect_ref`` field.
        On redo, rather than creating a brand-new DraggableRectangle — which
        would silently break every caller-held reference — this method:

        1. Re-creates the two canvas items (rectangle + resize handle) with fresh
           canvas IDs stored directly on ``rect.rect`` / ``rect.resize_handle``.
        2. Re-binds all mouse-event handlers to the new item IDs.
        3. Syncs Python-side visual attributes from the saved snapshot.
        4. Recreates attached items from snapshot.
        5. Re-registers the object in the class-level weakref instance list
           (which was pruned when ``delete()`` was called during undo).

        The net result is a live, fully interactive rectangle that is the *same*
        Python object as before undo, so all external references remain valid.

        Args:
            rect: The DraggableRectangle whose canvas items need to be recreated.
            data: A single object entry from a history state dictionary.
        """
        # Saved coords are in logical (zoom=1.0) space; scale to current canvas space.
        coords = self._logical_to_canvas_coords(data["coords"])
        outline = data.get("outline", "black")
        fill = data.get("fill", "")
        line_width = data.get("line_width", 5)
        handle_radius = data.get("handle_radius", 5)
        dpi = data.get("dpi", self.dpi)

        # Re-create the two underlying canvas items (fresh IDs, same Python object)
        rect.rect = self.create_rectangle(
            coords[0],
            coords[1],
            coords[2],
            coords[3],
            outline=outline,
            fill=fill,
            width=line_width,
        )
        rect.resize_handle = self.create_aa_circle(
            coords[2], coords[3], radius=handle_radius, fill="#00497b"
        )

        # Re-bind all mouse interaction events to the new canvas item IDs
        b = self._bindings
        self.tag_bind(rect.rect, b.mouse_left_click, rect.on_click)
        self.tag_bind(rect.rect, b.mouse_left_drag, rect.on_drag)
        self.tag_bind(rect.rect, b.mouse_left_release, rect._on_drag_end)
        self.tag_bind(rect.resize_handle, b.mouse_left_click, rect.on_resize_click)
        self.tag_bind(rect.resize_handle, b.mouse_left_drag, rect.on_resize_drag)
        self.tag_bind(rect.resize_handle, b.mouse_left_release, rect._on_resize_end)

        # Sync Python-side attribute state from the snapshot
        rect.original_outline = outline
        rect.fill_color = fill
        rect.line_width = line_width
        rect.handle_radius = handle_radius
        rect.dpi = dpi

        # Restore attached items from snapshot
        saved_attached = data.get("attached_items")
        if saved_attached:
            rect._attached_items.clear()
            for snapshot in saved_attached:
                canvas_snapshot = {
                    **snapshot,
                    "coords": self._logical_to_canvas_coords(snapshot["coords"]),
                }
                new_id = self._recreate_attached_item(canvas_snapshot)
                if new_id is not None:
                    rect._attached_items.append(new_id)

        # Re-register in class-level weakref tracking (removed by delete())
        rect_class = type(rect)
        if not any(ref is rect._self_ref for ref in rect_class._instances):
            rect_class._instances.append(rect._self_ref)

    def _restore_state(self, state: dict) -> None:
        """
        Restore canvas to a saved state via in-place reconciliation.

        Rather than a full destroy/rebuild cycle (which invalidates all external
        references to DraggableRectangle objects), this method reconciles the
        live canvas against the saved state in three targeted steps:

        1. Update in-place — items whose item_id exists in both the current
           canvas and the saved state are mutated directly (geometry + visuals).
           The Python object is not replaced, so all caller-held references
           remain valid after undo/redo.

        2. Delete surplus — items present only in the current canvas (not in
           the saved state) are removed, suppressing user callbacks.

        3. Resurrect missing — items present only in the saved state (previously
           deleted by the user) are recreated as new DraggableRectangle instances
           and registered under their original item_id.

        Flags _restoring_state and _suppress_registration prevent side effects
        throughout (no spurious deselect callbacks, no auto-registration
        conflicts from newly created rectangles).

        Args:
            state: A history state dictionary from save_state().
        """
        self._restoring_state = True
        self._suppress_registration = True

        try:
            # Normalise saved keys to int once for all three steps
            saved: Dict[int, Dict] = {
                (int(k) if isinstance(k, str) else k): v for k, v in state["objects"].items()
            }

            current_ids = set(self.objects.keys())
            saved_ids = set(saved.keys())

            # Step 1 — update surviving items in-place (preserves external references)
            for item_id in current_ids & saved_ids:
                self._update_rect_in_place(self.objects[item_id], saved[item_id])

            # Step 2 — remove items that do not exist in the saved state
            for item_id in list(current_ids - saved_ids):
                self.delete_draggable_rectangle(item_id)

            # Step 3 — resurrect items that exist in saved state but not currently.
            # When rect_ref is present (v0.4.2+), reuse the original Python object
            # so every caller-held reference stays valid after undo/redo.
            for item_id in saved_ids - current_ids:
                obj_data = saved[item_id]
                rect_ref = obj_data.get("rect_ref")
                if rect_ref is not None:
                    # Resurrect the original object — canvas items are recreated,
                    # events are rebound, but the Python identity is preserved.
                    self._resurrect_rect(rect_ref, obj_data)
                    self.objects[item_id] = rect_ref
                    # Re-register in reverse lookup maps
                    r_id = id(rect_ref)
                    self._registered_rects.add(r_id)
                    self._rect_to_id[r_id] = item_id
                else:
                    # Backward-compat fallback for states saved before v0.4.2
                    # (no rect_ref field). Creates a new object as before.
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
                    # Register in reverse lookup maps
                    r_id = id(rect)
                    self._registered_rects.add(r_id)
                    self._rect_to_id[r_id] = item_id

            # Restore next_item_id
            self.next_item_id = state["next_item_id"]

            # Reset selection state without firing callbacks, then restore from snapshot.
            # Only iterate previously-selected objects (not all objects).
            for obj in self.selected_objects.values():
                obj.set_is_selected(False)
                self.itemconfig(obj.rect, outline=obj.original_outline)
            self.selected_objects.clear()

            for item_id in state.get("selected", []):
                if item_id in self.objects:
                    self.select_item(item_id)

        finally:
            self._suppress_registration = False
            self._restoring_state = False

    # -------------------------------------------------------------------------
    # Zoom
    # -------------------------------------------------------------------------

    def zoom_in(self, factor: float = 1.2) -> None:
        """
        Zoom in on the canvas, centered on the current view.

        Scales all canvas items (rectangles, lines, text) via the native
        canvas.scale() call, then performs PIL-based resizing on any
        tracked images since canvas.scale() does not resize bitmaps.

        Args:
            factor: Zoom multiplier (default: 1.2)
        """
        self._dispatch("zoom_in", self._builtin_zoom_in, factor)

    def _builtin_zoom_in(self, factor: float = 1.2) -> None:
        if not self.enable_zoom:
            return
        new_zoom = self.zoom_level * factor
        if new_zoom <= self.max_zoom:
            cx, cy = self.get_view_center()
            # Keep origin in sync: canvas_coord = zoom * logical + origin
            # After scaling by f around cx: new_origin = f*old_origin + cx*(1-f)
            self._canvas_origin_x = factor * self._canvas_origin_x + cx * (1.0 - factor)
            self._canvas_origin_y = factor * self._canvas_origin_y + cy * (1.0 - factor)
            self.zoom_level = new_zoom
            self.scale("all", cx, cy, factor, factor)
            self._rescale_all_tracked_images()

    def zoom_out(self, factor: float = 1.2) -> None:
        """
        Zoom out on the canvas, centered on the current view.

        Args:
            factor: Zoom divisor (default: 1.2)
        """
        self._dispatch("zoom_out", self._builtin_zoom_out, factor)

    def _builtin_zoom_out(self, factor: float = 1.2) -> None:
        if not self.enable_zoom:
            return
        new_zoom = self.zoom_level / factor
        if new_zoom >= self.min_zoom:
            cx, cy = self.get_view_center()
            inv = 1.0 / factor
            self._canvas_origin_x = inv * self._canvas_origin_x + cx * (1.0 - inv)
            self._canvas_origin_y = inv * self._canvas_origin_y + cy * (1.0 - inv)
            self.zoom_level = new_zoom
            self.scale("all", cx, cy, inv, inv)
            self._rescale_all_tracked_images()

    def on_zoom_wheel(self, event: Event) -> None:
        """Handle Alt+MouseWheel zoom."""
        self._dispatch("on_zoom_wheel", self._builtin_on_zoom_wheel, event)

    def _builtin_on_zoom_wheel(self, event: Event) -> None:
        if not self.enable_zoom:
            return
        if event.delta > 0:
            self.zoom_in(1.1)
        else:
            self.zoom_out(1.1)

    # -------------------------------------------------------------------------
    # Image tracking
    # -------------------------------------------------------------------------

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
            from PIL import Image as PILImage
            from PIL import ImageTk
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

    def _canvas_to_logical_coords(self, coords: List[float]) -> List[float]:
        """Convert canvas-space coordinates to zoom=1.0 logical coordinates.

        The affine relationship is:
            canvas_coord = zoom_level * logical_coord + origin

        So the inverse is:
            logical_coord = (canvas_coord - origin) / zoom_level

        X- and Y-components alternate in *coords* (x0, y0, x1, y1, ...).
        """
        z = self.zoom_level
        ox = self._canvas_origin_x
        oy = self._canvas_origin_y
        if z == 1.0 and ox == 0.0 and oy == 0.0:
            return list(coords)
        iz = 1.0 / z
        return [(coords[i] - (ox if i % 2 == 0 else oy)) * iz for i in range(len(coords))]

    def _logical_to_canvas_coords(self, coords: List[float]) -> List[float]:
        """Convert zoom=1.0 logical coordinates to current canvas-space coordinates.

        Inverse of _canvas_to_logical_coords:
            canvas_coord = zoom_level * logical_coord + origin
        """
        z = self.zoom_level
        ox = self._canvas_origin_x
        oy = self._canvas_origin_y
        if z == 1.0 and ox == 0.0 and oy == 0.0:
            return list(coords)
        return [coords[i] * z + (ox if i % 2 == 0 else oy) for i in range(len(coords))]

    # -------------------------------------------------------------------------
    # Attached items
    # -------------------------------------------------------------------------

    def attach_text_to_rectangle(self, text_id: int, rect: DraggableRectangle) -> None:
        """
        Attach a text item to a rectangle so they move together.

        Args:
            text_id: Canvas text item ID
            rect: DraggableRectangle to attach text to
        """
        self._dispatch(
            "attach_text_to_rectangle",
            self._builtin_attach_text_to_rectangle,
            text_id,
            rect,
        )

    def _builtin_attach_text_to_rectangle(self, text_id: int, rect: DraggableRectangle) -> None:
        rect._attached_items.append(text_id)

    def move_attached_items(self, rect: DraggableRectangle, dx: float, dy: float) -> None:
        """
        Move items attached to a rectangle.

        Args:
            rect: Rectangle whose attached items should move
            dx: X displacement
            dy: Y displacement
        """
        self._dispatch(
            "move_attached_items",
            self._builtin_move_attached_items,
            rect,
            dx,
            dy,
        )

    def _builtin_move_attached_items(self, rect: DraggableRectangle, dx: float, dy: float) -> None:
        for item_id in rect._attached_items:
            self.move(item_id, dx, dy)

    def _snapshot_attached_items(self, rect: DraggableRectangle) -> List[Dict[str, Any]]:
        """
        Capture metadata of all canvas items attached to a rectangle.

        Returns a list of serialisable dictionaries — one per attached item —
        containing enough information to recreate the items later via
        ``_recreate_attached_item()``.

        Args:
            rect: The rectangle whose attached items should be snapshotted.

        Returns:
            List of snapshot dicts (empty if the rectangle has no attachments).
        """
        snapshots: List[Dict[str, Any]] = []
        for attached_id in rect._attached_items:
            try:
                item_type = self.type(attached_id)
                item_coords = self._canvas_to_logical_coords(list(self.coords(attached_id)))
                snapshot: Dict[str, Any] = {
                    "type": item_type,
                    "coords": item_coords,
                }
                if item_type == "text":
                    snapshot["text"] = self.itemcget(attached_id, "text")
                    snapshot["font"] = self.itemcget(attached_id, "font")
                    snapshot["fill"] = self.itemcget(attached_id, "fill")
                    snapshot["anchor"] = self.itemcget(attached_id, "anchor")
                elif item_type in ("line", "rectangle", "oval", "arc", "polygon"):
                    snapshot["fill"] = self.itemcget(attached_id, "fill")
                    snapshot["outline"] = self.itemcget(attached_id, "outline")
                    snapshot["width"] = self.itemcget(attached_id, "width")
                snapshot["tags"] = list(self.gettags(attached_id))
                snapshots.append(snapshot)
            except Exception:
                pass  # Item may have been deleted externally
        return snapshots

    def _recreate_attached_item(self, snapshot: Dict[str, Any]) -> Optional[int]:
        """
        Recreate a single canvas item from a snapshot dictionary.

        Args:
            snapshot: A dictionary previously produced by ``_snapshot_attached_items()``.

        Returns:
            The new canvas item ID, or ``None`` if the type is unsupported.
        """
        item_type = snapshot["type"]
        item_coords = snapshot["coords"]
        tags = tuple(snapshot.get("tags", ()))

        if item_type == "text":
            return cast(
                int,
                self.create_text(
                    *item_coords,
                    text=snapshot.get("text", ""),
                    font=snapshot.get("font", ""),
                    fill=snapshot.get("fill", "black"),
                    anchor=snapshot.get("anchor", "center"),
                    tags=tags,
                ),
            )
        elif item_type == "rectangle":
            return cast(
                int,
                self.create_rectangle(
                    *item_coords,
                    fill=snapshot.get("fill", ""),
                    outline=snapshot.get("outline", "black"),
                    width=float(snapshot.get("width", 1)),
                    tags=tags,
                ),
            )
        elif item_type == "line":
            return cast(
                int,
                self.create_line(
                    *item_coords,
                    fill=snapshot.get("fill", "black"),
                    width=float(snapshot.get("width", 1)),
                    tags=tags,
                ),
            )
        elif item_type == "oval":
            return cast(
                int,
                self.create_oval(
                    *item_coords,
                    fill=snapshot.get("fill", ""),
                    outline=snapshot.get("outline", "black"),
                    width=float(snapshot.get("width", 1)),
                    tags=tags,
                ),
            )
        return None

    # -------------------------------------------------------------------------
    # Grid overlay
    # -------------------------------------------------------------------------

    def add_grid(self, **kwargs: Any) -> CanvasGrid:
        """Create and attach an adaptive :class:`~ctk_interactive_canvas.CanvasGrid`.

        The returned grid is fully self-managing — it registers its own zoom /
        pan callbacks and redraws itself via ``after_idle`` whenever the view
        changes.  Call :meth:`~ctk_interactive_canvas.CanvasGrid.destroy` on
        the returned object to detach it.

        All keyword arguments are forwarded verbatim to
        :class:`~ctk_interactive_canvas.CanvasGrid`.  Common options::

            canvas.add_grid(spacing=50)
            canvas.add_grid(
                spacing=100,
                color="#888888",
                alpha=0.6,
                linestyle="--",
                subdivisions=4,
                show_origin=True,
            )

        Grid magnetism (snap-to-grid during drag and resize) is enabled by
        passing ``snap=True``::

            grid = canvas.add_grid(spacing=50, snap=True)
            # Reconfigure later:
            grid.snap.configure(snap_ratio=0.25, snap_y=False)
            grid.disable_snap()
            grid.enable_snap()

        Returns:
            The newly created :class:`~ctk_interactive_canvas.CanvasGrid` instance.
        """
        return CanvasGrid(self, **kwargs)
