"""Centralised event binding string constants.

``CanvasBindings`` is a frozen dataclass that names every tkinter event
sequence used by ``InteractiveCanvas`` and ``DraggableRectangle``.  All
fields default to the standard platform bindings, so ``CanvasBindings()``
reproduces the original behaviour without configuration.

To remap one or more bindings, construct a custom instance and pass it
to ``InteractiveCanvas``::

    from ctk_interactive_canvas import InteractiveCanvas, CanvasBindings

    canvas = InteractiveCanvas(
        app,
        bindings=CanvasBindings(
            zoom_in_plus="<KP_Add>",     # numpad + for zoom-in
            zoom_out_minus="<KP_Subtract>",
        ),
    )

``DEFAULT_BINDINGS`` is the module-level singleton used when no custom
instance is supplied.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class CanvasBindings:
    """Centralised event binding strings for ``InteractiveCanvas`` and ``DraggableRectangle``.

    All fields carry their default tkinter event sequences as default values,
    so a plain ``CanvasBindings()`` produces the standard binding set.
    Override individual fields by passing keyword arguments to the constructor.

    Groups:
        Mouse - common left- and middle-button sequences used at both the
            canvas level and the rectangle/resize-handle ``tag_bind`` level.
        Keyboard modifiers - Shift, Alt, and Ctrl press/release sequences
            consumed by ``DraggableRectangle`` for drag and resize constraints.
        Keyboard actions - Space (panning toggle) and Delete (object removal).
        History - undo/redo keyboard shortcuts bound by ``InteractiveCanvas``.
        Zoom - keyboard and mouse-wheel zoom shortcuts.
    """

    # ------------------------------------------------------------------
    # Mouse - shared by canvas-level bind() and rectangle tag_bind()
    # ------------------------------------------------------------------
    mouse_left_click: str = "<Button-1>"
    mouse_left_drag: str = "<B1-Motion>"
    mouse_left_release: str = "<ButtonRelease-1>"
    mouse_middle_click: str = "<ButtonPress-2>"
    mouse_middle_drag: str = "<B2-Motion>"
    mouse_middle_release: str = "<ButtonRelease-2>"

    # ------------------------------------------------------------------
    # Keyboard modifiers (DraggableRectangle drag / resize constraints)
    # ------------------------------------------------------------------
    shift_press: str = "<Shift_L>"
    shift_release: str = "<KeyRelease-Shift_L>"
    alt_press: str = "<Alt_L>"
    alt_release: str = "<KeyRelease-Alt_L>"
    ctrl_press: str = "<Control_L>"
    ctrl_release: str = "<KeyRelease-Control_L>"

    # ------------------------------------------------------------------
    # Keyboard actions (InteractiveCanvas)
    # ------------------------------------------------------------------
    space_press: str = "<KeyPress-space>"
    space_release: str = "<KeyRelease-space>"
    delete_key: str = "<Delete>"

    # ------------------------------------------------------------------
    # History shortcuts
    # ------------------------------------------------------------------
    undo: str = "<Control-z>"
    undo_upper: str = "<Control-Z>"
    redo_y: str = "<Control-y>"
    redo_y_upper: str = "<Control-Y>"
    redo_shift_z: str = "<Control-Shift-z>"
    redo_shift_z_upper: str = "<Control-Shift-Z>"

    # ------------------------------------------------------------------
    # Zoom shortcuts
    # ------------------------------------------------------------------
    zoom_in_plus: str = "<plus>"
    zoom_in_equal: str = "<equal>"
    zoom_out_minus: str = "<minus>"
    zoom_wheel: str = "<Alt-MouseWheel>"
    zoom_wheel_up: str = "<Alt-Button-4>"
    zoom_wheel_down: str = "<Alt-Button-5>"

    # ------------------------------------------------------------------
    # Clipboard shortcuts (copy / cut / paste / duplicate)
    # ------------------------------------------------------------------
    copy: str = "<Control-c>"
    copy_upper: str = "<Control-C>"
    cut: str = "<Control-x>"
    cut_upper: str = "<Control-X>"
    paste: str = "<Control-v>"
    paste_upper: str = "<Control-V>"
    duplicate: str = "<Control-d>"
    duplicate_upper: str = "<Control-D>"


#: Module-level default instance - used when no custom bindings are supplied.
DEFAULT_BINDINGS: CanvasBindings = CanvasBindings()
