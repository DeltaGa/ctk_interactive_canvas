"""CanvasGrid — adaptive, matplotlib-style virtual grid for InteractiveCanvas.

Virtual-grid design
-------------------
Lines are never subjected to ``canvas.scale()`` and never stored as persistent
canvas items.  On every view-state change (zoom, pan, resize) the entire grid
is deleted via a single ``canvas.delete(tag)`` call (O(1) in Tk's C layer) and
redrawn from the current logical→canvas coordinate transform.  The grid can
therefore never drift, merge, or vanish regardless of zoom level or pan offset.

Adaptive spacing
----------------
The effective logical spacing is doubled or halved automatically so that the
resulting pixel pitch stays within ``[min_px_spacing, max_px_spacing]``.  This
mirrors matplotlib's ``AutoLocator`` / ``AutoMinorLocator`` behaviour: zooming
in reveals finer subdivision; zooming out collapses them back.

Performance
-----------
- O(1) delete: ``canvas.delete(tag)`` in one C round-trip.
- ``after_idle`` batching: rapid sequential updates (e.g. 60 Hz pan drag)
  collapse into a single redraw per Tk event-loop frame.  The
  ``_pending_redraw`` boolean flag prevents duplicate ``after_idle`` enqueues.
- Hot-loop locals: ``canvas.create_line`` is bound once per ``_draw_grid_lines``
  call; ``zoom``, ``ox``, ``oy`` are read once and used inline — no repeated
  attribute lookups inside the sweep loops.
- No dict unpacking overhead: ``**common_kw`` is built once per layer.

Linestyles
----------
matplotlib shorthand strings map to tkinter ``dash`` tuples via a small
look-up table.  The empty tuple is the special "solid" sentinel (``dash``
keyword is omitted entirely to avoid an empty-dash tkinter warning).

Alpha
-----
Tkinter canvas items have no RGBA support.  Alpha is approximated by blending
the requested foreground color with the detected canvas background color using
linear RGB interpolation.  ``winfo_rgb`` is used to resolve any named color
(e.g. ``"gray"`` or ``"lightblue"``) to its true RGB value.
"""

import contextlib
import math
from tkinter import TclError
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from .interactive_canvas import InteractiveCanvas


# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

_TAG_MAJOR: str = "_ctk_grid_major"
_TAG_MINOR: str = "_ctk_grid_minor"

#: Maps matplotlib-style linestyle shorthand to tkinter dash tuples.
#: The empty tuple is the "solid" sentinel — ``dash`` is omitted from the
#: ``create_line`` call entirely when this value is chosen.
_DASH_MAP: dict[str, tuple[int, ...]] = {
    "-": (),
    "--": (8, 4),
    ":": (2, 4),
    "-.": (8, 4, 2, 4),
}

#: Frozenset of valid linestyle strings — exposed publicly for validation.
VALID_LINESTYLES: frozenset[str] = frozenset(_DASH_MAP)

#: Hard cap on lines drawn per axis per layer per frame.
#: Prevents pathological rendering if adaptive spacing fails to converge.
_MAX_LINES_PER_AXIS: int = 500

#: Maximum adaptive-spacing iteration count (log₂ safety bound).
_MAX_ADAPT_ITERS: int = 64

#: Default adaptive-spacing limits used by standalone GridSnap instances.
_SNAP_DEFAULT_MIN_PX: float = 10.0
_SNAP_DEFAULT_MAX_PX: float = 400.0

#: Maximum allowed snap_ratio value (half a grid cell = always snap to nearest).
_SNAP_RATIO_MAX: float = 0.5

# Hex color string lengths used in _parse_hex_rgb.
_HEX_SHORT: int = 3
_HEX_LONG: int = 6

# Simple configure() parameter → private attribute name mapping.
_SIMPLE_PARAMS: dict[str, str] = {
    "color": "_color",
    "alpha": "_alpha",
    "linewidth": "_linewidth",
    "minor_color": "_minor_color",
    "minor_alpha": "_minor_alpha",
    "minor_linewidth": "_minor_linewidth",
    "show_minor": "_show_minor",
    "show_origin": "_show_origin",
    "origin_color": "_origin_color",
    "origin_alpha": "_origin_alpha",
    "origin_linewidth": "_origin_linewidth",
    "enabled": "_enabled",
}


# ---------------------------------------------------------------------------
# Color utilities
# ---------------------------------------------------------------------------


def _resolve_color(canvas: Any, color: str) -> str:
    """Resolve any tkinter color to ``'#RRGGBB'`` using ``winfo_rgb``.

    Falls back to the original string on failure (e.g. before the canvas is
    mapped, or for unsupported color formats).

    Args:
        canvas: Any tkinter widget with ``winfo_rgb``.
        color: Any color string understood by tkinter.

    Returns:
        A ``'#RRGGBB'`` hex string, or the original ``color`` on failure.
    """
    try:
        r16, g16, b16 = canvas.winfo_rgb(color)
        return f"#{r16 >> 8:02x}{g16 >> 8:02x}{b16 >> 8:02x}"
    except TclError:
        return color


def _parse_hex_rgb(hex_color: str) -> Optional[tuple[int, int, int]]:
    """Parse ``'#RRGGBB'`` or ``'#RGB'`` to ``(r, g, b)`` in 0-255.

    Returns ``None`` on parse failure so callers can fall back gracefully.
    """
    try:
        c = hex_color.lstrip("#")
        if len(c) == _HEX_SHORT:
            c = c[0] * 2 + c[1] * 2 + c[2] * 2
        if len(c) != _HEX_LONG:
            return None
        return int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
    except (ValueError, TypeError):
        return None


def _blend_color(fg: str, alpha: float, bg: str) -> str:
    """Linear-interpolate *fg* over *bg* at opacity *alpha* ∈ [0, 1].

    Both *fg* and *bg* must be ``'#RRGGBB'`` strings (pre-resolved via
    :func:`_resolve_color`).  Returns the blended ``'#RRGGBB'`` string, or
    *fg* unchanged if either color cannot be parsed.

    Args:
        fg: Foreground color ``'#RRGGBB'``.
        alpha: Opacity in [0, 1].
        bg: Background color ``'#RRGGBB'``.

    Returns:
        Blended ``'#RRGGBB'`` color string.
    """
    alpha = max(0.0, min(1.0, alpha))
    if alpha >= 1.0:
        return fg
    fg_rgb = _parse_hex_rgb(fg)
    bg_rgb = _parse_hex_rgb(bg)
    if fg_rgb is None or bg_rgb is None:
        return fg
    ia = 1.0 - alpha
    r = int(fg_rgb[0] * alpha + bg_rgb[0] * ia)
    g = int(fg_rgb[1] * alpha + bg_rgb[1] * ia)
    b = int(fg_rgb[2] * alpha + bg_rgb[2] * ia)
    return f"#{r:02x}{g:02x}{b:02x}"


# ---------------------------------------------------------------------------
# CanvasGrid
# ---------------------------------------------------------------------------


class CanvasGrid:
    """Adaptive, matplotlib-style virtual grid overlay for InteractiveCanvas.

    The grid is always drawn below all rectangle and attached-item canvas
    objects.  It survives arbitrary zoom and pan without drifting, merging,
    or becoming invisible because it is never canvas-scaled — it is always
    redrawn from scratch using the current logical-to-canvas coordinate
    transform.

    Major / minor layers
    --------------------
    *Major* lines are spaced ``spacing`` logical units apart and styled via
    ``color``, ``alpha``, ``linestyle``, and ``linewidth``.  *Minor* lines
    subdivide each major interval into ``subdivisions`` cells and carry their
    own independent visual parameters.

    Adaptive density
    ----------------
    Both layers adapt automatically: when the pixel pitch would fall below
    ``min_px_spacing`` the effective spacing is doubled (fewer lines); when it
    would exceed ``max_px_spacing`` it is halved (more lines).  Minor lines
    additionally collapse entirely when their pixel pitch falls below
    ``min_px_spacing``.

    Optional origin axes
    --------------------
    When ``show_origin=True``, the x=0 and y=0 grid lines are drawn in a
    separate, more prominent style (``origin_color``, ``origin_linewidth``)
    and are unaffected by the adaptive spacing logic — they are always visible
    as long as the origin is within the viewport.

    Linestyles
    ----------
    Accepted values (matplotlib shorthand):

    =======  ========================
    ``'-'``  Solid line (default)
    ``'--'`` Dashed
    ``':'``  Dotted
    ``'-.'`` Dash-dot
    =======  ========================

    Alpha
    -----
    Tkinter canvas items do not support RGBA.  Alpha is approximated by
    blending the requested color with the canvas background.  The blended
    color is recomputed on every redraw so it remains correct if the canvas
    background color changes.

    Usage::

        canvas = InteractiveCanvas(app)

        # Via the convenience factory (recommended)
        grid = canvas.add_grid(spacing=50, color="#aaaaaa", alpha=0.7)

        # Or standalone
        from ctk_interactive_canvas import CanvasGrid
        grid = CanvasGrid(canvas, spacing=50, show_origin=True)

        grid.configure(color="blue", linestyle="--")
        grid.hide()
        grid.show()
        grid.destroy()

    Args:
        canvas: The ``InteractiveCanvas`` (or compatible ``CTkCanvas``) to
            overlay.  Must support ``canvasx``/``canvasy`` and ideally expose
            ``zoom_level``, ``_canvas_origin_x``, and ``_canvas_origin_y``.
        spacing: Distance between major grid lines in *logical* (zoom=1)
            units.  Default: ``50.0``.
        subdivisions: Number of minor grid cells per major interval.
            Default: ``5``.
        color: Major-line color — any tkinter color name or ``'#RRGGBB'`` hex.
            Default: ``"#aaaaaa"``.
        alpha: Major-line opacity in [0, 1].  Approximated via background
            blending.  Default: ``1.0``.
        linestyle: Major-line style, one of ``'-'``, ``'--'``, ``':'``,
            ``'-.'``.  Default: ``'-'``.
        linewidth: Major-line width in screen pixels.  Default: ``1.0``.
        minor_color: Minor-line color.  Defaults to ``color``.
        minor_alpha: Minor-line opacity.  Defaults to ``alpha * 0.4``.
        minor_linestyle: Minor-line style.  Default: ``':'``.
        minor_linewidth: Minor-line width.  Default: ``1.0``.
        show_minor: Draw minor subdivision lines.  Default: ``True``.
        show_origin: Draw prominent x=0 and y=0 axis lines.  Default:
            ``False``.
        origin_color: Color for origin axes when ``show_origin=True``.
            Default: ``"#555555"``.
        origin_alpha: Opacity for origin axes.  Default: ``1.0``.
        origin_linewidth: Line width for origin axes.  Default: ``2.0``.
        min_px_spacing: Pixel pitch below which spacing adapts upward
            (fewer lines).  Default: ``10.0``.
        max_px_spacing: Pixel pitch above which spacing adapts downward
            (more lines).  Default: ``400.0``.
        enabled: Master visibility switch.  Default: ``True``.
        snap: Enable grid magnetism immediately.  Default: ``False``.
        snap_ratio: Snap attraction radius as a fraction of the effective
            grid cell size in (0, 0.5].  ``0.5`` snaps to the nearest line
            on every drag event (hard-snap); smaller values create a soft
            magnet that only activates near a line.  Default: ``0.5``.
        snap_x: Snap horizontally.  Default: ``True``.
        snap_y: Snap vertically.  Default: ``True``.
        snap_move: Snap during move (drag) operations.  Default: ``True``.
        snap_resize: Snap during resize-handle operations.  Default: ``True``.
    """

    def __init__(
        self,
        canvas: "InteractiveCanvas",
        spacing: float = 50.0,
        subdivisions: int = 5,
        color: str = "#aaaaaa",
        alpha: float = 1.0,
        linestyle: str = "-",
        linewidth: float = 1.0,
        minor_color: Optional[str] = None,
        minor_alpha: Optional[float] = None,
        minor_linestyle: str = ":",
        minor_linewidth: float = 1.0,
        show_minor: bool = True,
        show_origin: bool = False,
        origin_color: str = "#555555",
        origin_alpha: float = 1.0,
        origin_linewidth: float = 2.0,
        min_px_spacing: float = 10.0,
        max_px_spacing: float = 400.0,
        enabled: bool = True,
        snap: bool = False,
        snap_ratio: float = 0.5,
        snap_x: bool = True,
        snap_y: bool = True,
        snap_move: bool = True,
        snap_resize: bool = True,
    ) -> None:
        # --- Input validation ------------------------------------------------
        if linestyle not in VALID_LINESTYLES:
            raise ValueError(
                f"linestyle must be one of {sorted(VALID_LINESTYLES)!r}, got {linestyle!r}"
            )
        if minor_linestyle not in VALID_LINESTYLES:
            raise ValueError(
                f"minor_linestyle must be one of {sorted(VALID_LINESTYLES)!r}, "
                f"got {minor_linestyle!r}"
            )
        if spacing <= 0:
            raise ValueError(f"spacing must be positive, got {spacing}")
        if subdivisions < 1:
            raise ValueError(f"subdivisions must be >= 1, got {subdivisions}")
        if min_px_spacing <= 0:
            raise ValueError(f"min_px_spacing must be positive, got {min_px_spacing}")
        if max_px_spacing <= min_px_spacing:
            raise ValueError("max_px_spacing must be > min_px_spacing")

        # --- Canvas reference ------------------------------------------------
        self._canvas = canvas

        # --- Major layer parameters ------------------------------------------
        self._spacing: float = spacing
        self._subdivisions: int = subdivisions
        self._color: str = color
        self._alpha: float = alpha
        self._linestyle: str = linestyle
        self._linewidth: float = linewidth

        # --- Minor layer parameters ------------------------------------------
        self._minor_color: str = minor_color if minor_color is not None else color
        self._minor_alpha: float = minor_alpha if minor_alpha is not None else alpha * 0.4
        self._minor_linestyle: str = minor_linestyle
        self._minor_linewidth: float = minor_linewidth
        self._show_minor: bool = show_minor

        # --- Origin axes parameters ------------------------------------------
        self._show_origin: bool = show_origin
        self._origin_color: str = origin_color
        self._origin_alpha: float = origin_alpha
        self._origin_linewidth: float = origin_linewidth

        # --- Adaptive spacing limits -----------------------------------------
        self._min_px_spacing: float = min_px_spacing
        self._max_px_spacing: float = max_px_spacing

        # --- State -----------------------------------------------------------
        self._enabled: bool = enabled
        self._pending_redraw: bool = False

        # Registered hook callbacks: (hook_name, fn, mode) for cleanup.
        self._hook_callbacks: list[tuple[str, Any, str]] = []
        # Direct tkinter bindings: (widget, event_sequence, funcid) for cleanup.
        self._bound_events: list[tuple[Any, str, str]] = []

        # --- Snap ------------------------------------------------------------
        self._snap_instance: Optional[GridSnap] = None
        if snap:
            self._snap_instance = GridSnap(
                canvas,
                grid=self,
                snap_ratio=snap_ratio,
                snap_x=snap_x,
                snap_y=snap_y,
                snap_move=snap_move,
                snap_resize=snap_resize,
            )

        # --- Wire up view-change notifications and draw ----------------------
        self._register_hooks()
        self._schedule_redraw()

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def show(self) -> None:
        """Make the grid visible and trigger an immediate redraw."""
        self._enabled = True
        self._schedule_redraw()

    def hide(self) -> None:
        """Hide the grid without destroying it.

        A subsequent :meth:`show` restores the grid without re-construction.
        """
        self._enabled = False
        self._canvas.delete(_TAG_MAJOR)
        self._canvas.delete(_TAG_MINOR)

    def configure(self, **kwargs: Any) -> None:
        """Live-reconfigure one or more grid parameters.

        Any constructor keyword argument may be updated.  The grid is
        redrawn immediately after the new values take effect.

        Args:
            **kwargs: Parameter names and new values (see class docstring).

        Raises:
            ValueError: If an invalid linestyle is given, ``spacing`` is
                non-positive, ``subdivisions`` < 1, or spacing limits are
                inconsistent.
            TypeError: If an unknown parameter name is supplied.
        """
        self._apply_spacing_kwargs(kwargs)

        # Validate and apply linestyles (loop keeps branch count ≤ 12).
        for ls_kwarg, ls_attr in (
            ("linestyle", "_linestyle"),
            ("minor_linestyle", "_minor_linestyle"),
        ):
            if ls_kwarg in kwargs:
                ls = kwargs.pop(ls_kwarg)
                if ls not in VALID_LINESTYLES:
                    raise ValueError(
                        f"{ls_kwarg} must be one of {sorted(VALID_LINESTYLES)!r}, got {ls!r}"
                    )
                setattr(self, ls_attr, ls)

        if "min_px_spacing" in kwargs or "max_px_spacing" in kwargs:
            new_min = float(kwargs.pop("min_px_spacing", self._min_px_spacing))
            new_max = float(kwargs.pop("max_px_spacing", self._max_px_spacing))
            if new_min <= 0:
                raise ValueError(f"min_px_spacing must be positive, got {new_min}")
            if new_max <= new_min:
                raise ValueError("max_px_spacing must be > min_px_spacing")
            self._min_px_spacing = new_min
            self._max_px_spacing = new_max

        for key, attr in _SIMPLE_PARAMS.items():
            if key in kwargs:
                setattr(self, attr, kwargs.pop(key))

        if kwargs:
            raise TypeError(f"Unknown configure parameter(s): {list(kwargs)}")

        self._schedule_redraw()

    def redraw(self) -> None:
        """Force a synchronous redraw, bypassing the ``after_idle`` queue."""
        self._pending_redraw = False
        self._redraw()

    def destroy(self) -> None:
        """Remove all grid items from the canvas and unregister all hooks.

        After calling this method the :class:`CanvasGrid` instance is inert
        and should be discarded.
        """
        self._canvas.delete(_TAG_MAJOR)
        self._canvas.delete(_TAG_MINOR)

        for hook_name, fn, mode in self._hook_callbacks:
            with contextlib.suppress(Exception):
                self._canvas.unregister_callback(hook_name, fn, mode)
        self._hook_callbacks.clear()

        for widget, event_seq, funcid in self._bound_events:
            with contextlib.suppress(Exception):
                widget.unbind(event_seq, funcid)
        self._bound_events.clear()

        if self._snap_instance is not None:
            self._snap_instance.destroy()
            self._snap_instance = None

    # -------------------------------------------------------------------------
    # Snap API
    # -------------------------------------------------------------------------

    @property
    def snap(self) -> Optional["GridSnap"]:
        """The attached :class:`GridSnap` instance, or ``None`` if snap is disabled."""
        return self._snap_instance

    def enable_snap(
        self,
        snap_ratio: float = 0.5,
        snap_x: bool = True,
        snap_y: bool = True,
        snap_move: bool = True,
        snap_resize: bool = True,
    ) -> "GridSnap":
        """Attach grid magnetism to this grid, or reconfigure the existing one.

        Calling this on an already-snapping grid updates the snap parameters
        without destroying and recreating the ``GridSnap`` instance.

        Args:
            snap_ratio: Snap attraction radius as a fraction of the effective
                grid cell size in (0, 0.5].  ``0.5`` = hard-snap to nearest.
            snap_x: Snap horizontally.
            snap_y: Snap vertically.
            snap_move: Snap during drag-move operations.
            snap_resize: Snap during drag-resize operations.

        Returns:
            The (possibly new) :class:`GridSnap` instance.
        """
        if self._snap_instance is not None:
            self._snap_instance.configure(
                snap_ratio=snap_ratio,
                snap_x=snap_x,
                snap_y=snap_y,
                snap_move=snap_move,
                snap_resize=snap_resize,
                enabled=True,
            )
        else:
            self._snap_instance = GridSnap(
                self._canvas,
                grid=self,
                snap_ratio=snap_ratio,
                snap_x=snap_x,
                snap_y=snap_y,
                snap_move=snap_move,
                snap_resize=snap_resize,
            )
        return self._snap_instance

    def disable_snap(self) -> None:
        """Disable grid magnetism without destroying the :class:`GridSnap` instance.

        A subsequent :meth:`enable_snap` call re-activates snapping without
        re-registering hooks.
        """
        if self._snap_instance is not None:
            self._snap_instance.disable()

    # -------------------------------------------------------------------------
    # Private helpers
    # -------------------------------------------------------------------------

    def _apply_spacing_kwargs(self, kwargs: dict[str, Any]) -> None:
        """Validate and consume ``spacing`` and ``subdivisions`` from *kwargs*.

        Extracted to keep :meth:`configure` within the ruff PLR0912 branch
        limit (≤ 12 branches).
        """
        if "spacing" in kwargs:
            v = float(kwargs.pop("spacing"))
            if v <= 0:
                raise ValueError(f"spacing must be positive, got {v}")
            self._spacing = v

        if "subdivisions" in kwargs:
            v_i = int(kwargs.pop("subdivisions"))
            if v_i < 1:
                raise ValueError(f"subdivisions must be >= 1, got {v_i}")
            self._subdivisions = v_i

    # -------------------------------------------------------------------------
    # Hook / binding registration
    # -------------------------------------------------------------------------

    def _register_hooks(self) -> None:
        """Wire up all view-change notifications on the parent canvas."""
        canvas = self._canvas

        # Use the InteractiveCanvas callback system for zoom and middle-drag pan.
        if hasattr(canvas, "register_callback"):
            for hook in ("zoom_in", "zoom_out", "on_middle_drag"):
                canvas.register_callback(hook, self._on_view_changed, "after")
                self._hook_callbacks.append((hook, self._on_view_changed, "after"))

        # <Configure> fires when the canvas widget is resized.  add=True stacks
        # our handler on top of any existing Configure binding.
        configure_funcid = canvas.bind("<Configure>", self._on_configure, True)
        if configure_funcid:
            self._bound_events.append((canvas, "<Configure>", configure_funcid))

        # <B1-Motion> covers the space+drag panning path.  We gate inside the
        # handler on canvas.panning so we do not redraw during drag-select.
        b1_funcid = canvas.bind("<B1-Motion>", self._on_b1_motion, True)
        if b1_funcid:
            self._bound_events.append((canvas, "<B1-Motion>", b1_funcid))

    # -------------------------------------------------------------------------
    # Event / hook callbacks
    # -------------------------------------------------------------------------

    def _on_view_changed(self, *_args: Any, **_kwargs: Any) -> None:
        """Callback for zoom and middle-drag pan hooks (accepts any signature)."""
        self._schedule_redraw()

    def _on_configure(self, _event: Any) -> None:
        """Callback for canvas widget resize."""
        self._schedule_redraw()

    def _on_b1_motion(self, _event: Any) -> None:
        """Callback for B1-Motion; redraws only during space+drag panning."""
        if getattr(self._canvas, "panning", False):
            self._schedule_redraw()

    # -------------------------------------------------------------------------
    # Redraw scheduling
    # -------------------------------------------------------------------------

    def _schedule_redraw(self) -> None:
        """Enqueue a single ``after_idle`` redraw for the next event-loop frame.

        Subsequent calls within the same frame are collapsed into the single
        already-pending redraw via the ``_pending_redraw`` guard flag, keeping
        the cost of rapid pan/zoom events to one redraw per frame.
        """
        if not self._pending_redraw:
            self._pending_redraw = True
            self._canvas.after_idle(self._redraw)

    # -------------------------------------------------------------------------
    # Core redraw
    # -------------------------------------------------------------------------

    def _redraw(self) -> None:
        """Delete all grid items and repaint them for the current view state.

        This is the only method that writes to the canvas.  It is always
        called via ``after_idle`` (or the synchronous :meth:`redraw` fallback)
        so it never fires in the middle of a Tk event handler.
        """
        self._pending_redraw = False
        canvas = self._canvas

        # Clear previous grid items (single C round-trip each).
        canvas.delete(_TAG_MAJOR)
        canvas.delete(_TAG_MINOR)

        if not self._enabled:
            return

        # --- Viewport dimensions --------------------------------------------
        w = canvas.winfo_width()
        h = canvas.winfo_height()
        if w <= 1:
            w = canvas.winfo_reqwidth()
        if h <= 1:
            h = canvas.winfo_reqheight()
        if w <= 0 or h <= 0:
            return

        # Canvas-space viewport corners (accounts for scroll offset).
        vx0 = canvas.canvasx(0)
        vy0 = canvas.canvasy(0)
        vx1 = canvas.canvasx(w)
        vy1 = canvas.canvasy(h)

        # --- Zoom transform (read once; used inline for speed) --------------
        # These attributes are unconditionally initialised by InteractiveCanvas
        # even when zoom is disabled, so getattr fallbacks are safe.
        zoom: float = getattr(canvas, "zoom_level", 1.0)
        ox: float = getattr(canvas, "_canvas_origin_x", 0.0)
        oy: float = getattr(canvas, "_canvas_origin_y", 0.0)

        # --- Logical-space viewport bounds ----------------------------------
        if zoom == 1.0 and ox == 0.0 and oy == 0.0:
            lx0, ly0, lx1, ly1 = vx0, vy0, vx1, vy1
        else:
            iz = 1.0 / zoom
            lx0 = (vx0 - ox) * iz
            ly0 = (vy0 - oy) * iz
            lx1 = (vx1 - ox) * iz
            ly1 = (vy1 - oy) * iz

        # --- Resolve display colors (re-resolved each frame for bg accuracy) --
        bg = "#ffffff"
        with contextlib.suppress(Exception):
            bg = _resolve_color(canvas, canvas.cget("background"))

        major_color = _blend_color(_resolve_color(canvas, self._color), self._alpha, bg)
        minor_color = _blend_color(_resolve_color(canvas, self._minor_color), self._minor_alpha, bg)

        # --- Adaptive major spacing -----------------------------------------
        maj_logical = self._adaptive_spacing(self._spacing, zoom)

        # --- Minor layer ----------------------------------------------------
        if self._show_minor and self._subdivisions > 1:
            min_logical = maj_logical / self._subdivisions
            if min_logical * zoom >= self._min_px_spacing:
                self._draw_grid_lines(
                    min_logical,
                    lx0,
                    ly0,
                    lx1,
                    ly1,
                    vx0,
                    vy0,
                    vx1,
                    vy1,
                    zoom,
                    ox,
                    oy,
                    _DASH_MAP[self._minor_linestyle],
                    self._minor_linewidth,
                    minor_color,
                    _TAG_MINOR,
                )

        # --- Major layer ----------------------------------------------------
        self._draw_grid_lines(
            maj_logical,
            lx0,
            ly0,
            lx1,
            ly1,
            vx0,
            vy0,
            vx1,
            vy1,
            zoom,
            ox,
            oy,
            _DASH_MAP[self._linestyle],
            self._linewidth,
            major_color,
            _TAG_MAJOR,
        )

        # --- Origin axes (drawn into the major tag, same z-order) -----------
        if self._show_origin:
            origin_color = _blend_color(
                _resolve_color(canvas, self._origin_color), self._origin_alpha, bg
            )
            self._draw_origin_axes(
                lx0,
                ly0,
                lx1,
                ly1,
                vx0,
                vy0,
                vx1,
                vy1,
                ox,
                oy,
                origin_color,
            )

        # --- Z-order: minor → major → rectangles (bottom to top) -----------
        # lower(_TAG_MAJOR) pushes major below all non-grid items.
        # lower(_TAG_MINOR) pushes minor below major.
        canvas.lower(_TAG_MAJOR)
        canvas.lower(_TAG_MINOR)

    # -------------------------------------------------------------------------
    # Adaptive spacing
    # -------------------------------------------------------------------------

    def _adaptive_spacing(self, base: float, zoom: float) -> float:
        """Compute the effective logical spacing so pixel pitch ∈ [min, max].

        Doubles the spacing when lines are too dense (pixel pitch < min);
        halves it when they are too sparse (pixel pitch > max), but never
        halves below the min threshold.

        Args:
            base: The configured base logical spacing.
            zoom: The current canvas zoom level.

        Returns:
            Effective logical spacing in logical units.
        """
        effective = base
        px = effective * zoom

        # Too dense → increase spacing (fewer lines).
        for _ in range(_MAX_ADAPT_ITERS):
            if px >= self._min_px_spacing:
                break
            effective *= 2.0
            px *= 2.0

        # Too sparse → decrease spacing (more lines), only if halving stays
        # above the minimum pixel threshold.
        for _ in range(_MAX_ADAPT_ITERS):
            if px <= self._max_px_spacing:
                break
            half_px = px * 0.5
            if half_px < self._min_px_spacing:
                break
            effective *= 0.5
            px = half_px

        return effective

    # -------------------------------------------------------------------------
    # Line drawing helpers
    # -------------------------------------------------------------------------

    def _draw_grid_lines(
        self,
        logical_spacing: float,
        lx0: float,
        ly0: float,
        lx1: float,
        ly1: float,
        vx0: float,
        vy0: float,
        vx1: float,
        vy1: float,
        zoom: float,
        ox: float,
        oy: float,
        dash: tuple[int, ...],
        width: float,
        color: str,
        tag: str,
    ) -> None:
        """Rasterise one grid layer (major or minor) onto the canvas.

        Sweeps across the logical-space viewport in both x and y, converting
        each grid coordinate to canvas space and creating one tkinter line per
        grid position.  Lines span the full pixel-space viewport so no clipping
        artefacts occur at the edges.

        Silently returns (no lines drawn) if ``logical_spacing`` is zero or
        the line count would exceed :data:`_MAX_LINES_PER_AXIS`.

        Args:
            logical_spacing: Spacing between consecutive lines in logical units.
            lx0, ly0, lx1, ly1: Logical-space viewport bounds.
            vx0, vy0, vx1, vy1: Canvas-space viewport bounds (line endpoints).
            zoom: Current zoom level (logical → canvas scale factor).
            ox, oy: Canvas origin offsets (logical → canvas translation).
            dash: Tkinter dash tuple (empty = solid).
            width: Line width in screen pixels.
            color: Pre-blended fill color string.
            tag: Canvas tag applied to every created item.
        """
        if logical_spacing <= 0.0:
            return

        # Safety cap: skip if line density would exceed the per-axis maximum.
        if (lx1 - lx0) / logical_spacing > _MAX_LINES_PER_AXIS:
            return
        if (ly1 - ly0) / logical_spacing > _MAX_LINES_PER_AXIS:
            return

        # Bind create_line once — avoids repeated attribute lookup inside loops.
        create_line = self._canvas.create_line

        # Build the shared keyword dict once for this layer.
        # Omitting 'dash' entirely (rather than passing an empty tuple) sidesteps
        # a tkinter issue that treats dash=() as "use previous dash pattern".
        common_kw: dict[str, Any] = {"fill": color, "width": width, "tags": tag}
        if dash:
            common_kw["dash"] = dash

        # --- Vertical lines (constant x, sweep in x) -----------------------
        first_lx = math.floor(lx0 / logical_spacing) * logical_spacing
        lx = first_lx
        lx1_guard = lx1 + logical_spacing * 0.5
        while lx <= lx1_guard:
            cx = lx * zoom + ox
            create_line(cx, vy0, cx, vy1, **common_kw)
            lx += logical_spacing

        # --- Horizontal lines (constant y, sweep in y) ---------------------
        first_ly = math.floor(ly0 / logical_spacing) * logical_spacing
        ly = first_ly
        ly1_guard = ly1 + logical_spacing * 0.5
        while ly <= ly1_guard:
            cy = ly * zoom + oy
            create_line(vx0, cy, vx1, cy, **common_kw)
            ly += logical_spacing

    def _draw_origin_axes(
        self,
        lx0: float,
        ly0: float,
        lx1: float,
        ly1: float,
        vx0: float,
        vy0: float,
        vx1: float,
        vy1: float,
        ox: float,
        oy: float,
        color: str,
    ) -> None:
        """Draw the x=0 and y=0 axis lines when they intersect the viewport.

        The axes are drawn into the major tag so they sit in the same z-order
        layer and are removed/recreated with the rest of the major grid.

        Args:
            lx0, ly0, lx1, ly1: Logical-space viewport bounds.
            vx0, vy0, vx1, vy1: Canvas-space viewport bounds (endpoints).
            ox, oy: Canvas origin offsets from the current transform.
            color: Pre-blended axis line color.
        """
        canvas = self._canvas
        origin_kw: dict[str, Any] = {
            "fill": color,
            "width": self._origin_linewidth,
            "tags": _TAG_MAJOR,
        }

        # Vertical axis (x = 0): visible only when x=0 is within viewport.
        if lx0 <= 0.0 <= lx1:
            canvas.create_line(ox, vy0, ox, vy1, **origin_kw)

        # Horizontal axis (y = 0): visible only when y=0 is within viewport.
        if ly0 <= 0.0 <= ly1:
            canvas.create_line(vx0, oy, vx1, oy, **origin_kw)


# ---------------------------------------------------------------------------
# GridSnap — grid magnetism for move and resize operations
# ---------------------------------------------------------------------------


class GridSnap:
    """Grid magnetism: snaps dragged/resized rectangles to the visible grid.

    Every mouse-move event during a drag or resize is intercepted via
    ``InteractiveCanvas`` after-hooks.  The snap correction is computed in
    canvas-space (accounting for zoom and pan), applied to **all** selected
    rectangles together so multi-selection layouts are preserved, and is
    visually instant — elements snap as the drag happens, not on release.

    Snap algorithm — ideal-position tracking
    -----------------------------------------
    The key design insight: snap must be computed against the *ideal* position
    (where the element would be without any snap correction), not the post-snap
    position.  Without this, every small per-frame mouse delta is immediately
    cancelled by the snap correction and the element locks permanently to the
    last grid line regardless of how far the mouse has moved.

    On ``rect_on_click`` / ``rect_on_resize_click``, the element's canvas
    position and the mouse widget-space position are recorded as the drag
    origin.  On every subsequent ``rect_on_drag`` / ``rect_on_resize_drag``
    frame:

    1. Compute the *ideal* snap anchor::

           ideal = origin_canvas_pos + (event_widget_pos - click_widget_pos)

       This is always the true mouse-accumulated position regardless of snap.

    2. Compute the nearest grid line to *ideal* and the snap correction::

           snapped_logical = round(ideal_logical / spacing) * spacing
           correction = snapped_canvas - ideal_canvas

    3. Apply the correction only when ``|correction| <= px_spacing * snap_ratio``.
       When the mouse has drifted past the snap threshold the correction is zero
       and the element follows the mouse freely until it nears the next line.

    4. Bring the element from its current canvas position to
       ``ideal + correction`` in a single ``canvas.move`` call.

    With ``snap_ratio=0.5`` the threshold is half the pixel pitch — the element
    always snaps to the nearest line and jumps to the next one when the mouse
    crosses the midpoint (hard-snap, Figma-style).  Smaller values give a soft
    magnet that engages only near lines.

    On ``rect_on_drag_end`` / ``rect_on_resize_end`` the per-drag state is
    cleared, ready for the next interaction.

    Effective spacing
    -----------------
    When a :class:`CanvasGrid` is linked (the common case), the snap uses the
    same adaptive spacing the grid displays — zooming in automatically reveals
    finer snap resolution.  When used standalone, the same adaptive algorithm
    is applied to the configured ``spacing``.

    Hot-path cost
    -------------
    Two ``canvas.coords()`` reads and N*2 ``canvas.move()`` writes per frame
    where N is the number of selected objects.  When the element is already at
    the snapped position ``apply_dx == apply_dy == 0`` and no canvas calls are
    made.

    Usage::

        grid = canvas.add_grid(spacing=50, snap=True)

        # Live reconfigure
        grid.snap.configure(snap_ratio=0.25, snap_x=True, snap_y=False)

        # Standalone (no visual grid needed)
        from ctk_interactive_canvas import GridSnap
        snapper = GridSnap(canvas, spacing=25)

    Args:
        canvas: The ``InteractiveCanvas`` instance to attach to.
        grid: Optional linked :class:`CanvasGrid` for adaptive spacing.
            When ``None``, ``spacing`` is used with the default adaptive
            limits (10 px min, 400 px max pitch).
        spacing: Grid spacing in logical units used when ``grid`` is ``None``.
            Default: ``50.0``.
        snap_ratio: Snap attraction radius as a fraction of the effective
            grid cell size in *(0, 0.5]*.  ``0.5`` = always snap to nearest
            (hard-snap); ``0.25`` = soft magnet within 25 % of cell width.
            Default: ``0.5``.
        snap_x: Enable horizontal snapping.  Default: ``True``.
        snap_y: Enable vertical snapping.  Default: ``True``.
        snap_move: Snap during drag-move operations.  Default: ``True``.
        snap_resize: Snap during resize-handle operations.  Default: ``True``.
        enabled: Master on/off switch.  Default: ``True``.
    """

    def __init__(
        self,
        canvas: "InteractiveCanvas",
        grid: Optional[CanvasGrid] = None,
        spacing: float = 50.0,
        snap_ratio: float = 0.5,
        snap_x: bool = True,
        snap_y: bool = True,
        snap_move: bool = True,
        snap_resize: bool = True,
        enabled: bool = True,
    ) -> None:
        if not (0.0 < snap_ratio <= _SNAP_RATIO_MAX):
            raise ValueError(f"snap_ratio must be in (0, {_SNAP_RATIO_MAX}], got {snap_ratio}")
        if spacing <= 0:
            raise ValueError(f"spacing must be positive, got {spacing}")

        self._canvas = canvas
        self._grid = grid
        self._spacing = spacing
        self._snap_ratio = snap_ratio
        self._snap_x = snap_x
        self._snap_y = snap_y
        self._snap_move = snap_move
        self._snap_resize = snap_resize
        self._enabled = enabled

        # --- Ideal-position tracking state -----------------------------------
        # Populated on rect_on_click / rect_on_resize_click; cleared on *_end.
        # Keyed by id(rect) so concurrent drag sessions stay isolated.
        #
        # _drag_click_mouse[id(r)]  = (widget_x, widget_y) at click time
        # _drag_click_rect[id(r)]   = (canvas_x0, canvas_y0) of TL at click
        # _resize_click_mouse[id(r)]= (widget_x, widget_y) at resize-click
        # _resize_click_rect[id(r)] = (canvas_x1, canvas_y1) of BR at click
        self._drag_click_mouse: dict[int, tuple[float, float]] = {}
        self._drag_click_rect: dict[int, tuple[float, float]] = {}
        self._resize_click_mouse: dict[int, tuple[float, float]] = {}
        self._resize_click_rect: dict[int, tuple[float, float]] = {}

        # Registered hook entries for cleanup: (hook_name, fn, mode).
        self._hook_callbacks: list[tuple[str, Any, str]] = []
        self._register_hooks()

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def enable(self) -> None:
        """Enable grid magnetism."""
        self._enabled = True

    def disable(self) -> None:
        """Disable grid magnetism without unregistering hooks."""
        self._enabled = False

    def configure(self, **kwargs: Any) -> None:
        """Live-reconfigure snap parameters.

        Args:
            spacing: Grid spacing in logical units (standalone mode only).
            snap_ratio: Attraction radius as a fraction of cell size (0, 0.5].
            snap_x: Snap horizontally.
            snap_y: Snap vertically.
            snap_move: Snap during move operations.
            snap_resize: Snap during resize operations.
            enabled: Master on/off switch.

        Raises:
            ValueError: If ``snap_ratio`` is out of range or ``spacing`` <= 0.
            TypeError: If an unknown parameter name is supplied.
        """
        _valid = frozenset(
            {"spacing", "snap_ratio", "snap_x", "snap_y", "snap_move", "snap_resize", "enabled"}
        )
        unknown = set(kwargs) - _valid
        if unknown:
            raise TypeError(f"Unknown GridSnap parameter(s): {sorted(unknown)}")

        if "spacing" in kwargs:
            v = float(kwargs["spacing"])
            if v <= 0:
                raise ValueError(f"spacing must be positive, got {v}")
            self._spacing = v
        if "snap_ratio" in kwargs:
            v2 = float(kwargs["snap_ratio"])
            if not (0.0 < v2 <= _SNAP_RATIO_MAX):
                raise ValueError(f"snap_ratio must be in (0, {_SNAP_RATIO_MAX}], got {v2}")
            self._snap_ratio = v2
        if "snap_x" in kwargs:
            self._snap_x = bool(kwargs["snap_x"])
        if "snap_y" in kwargs:
            self._snap_y = bool(kwargs["snap_y"])
        if "snap_move" in kwargs:
            self._snap_move = bool(kwargs["snap_move"])
        if "snap_resize" in kwargs:
            self._snap_resize = bool(kwargs["snap_resize"])
        if "enabled" in kwargs:
            self._enabled = bool(kwargs["enabled"])

    def destroy(self) -> None:
        """Unregister all hooks and make this instance inert."""
        for hook_name, fn, mode in self._hook_callbacks:
            with contextlib.suppress(Exception):
                self._canvas.unregister_callback(hook_name, fn, mode)
        self._hook_callbacks.clear()
        self._drag_click_mouse.clear()
        self._drag_click_rect.clear()
        self._resize_click_mouse.clear()
        self._resize_click_rect.clear()

    # -------------------------------------------------------------------------
    # Hook registration
    # -------------------------------------------------------------------------

    def _register_hooks(self) -> None:
        """Register after-hooks for all six drag lifecycle events."""
        canvas = self._canvas
        if not hasattr(canvas, "register_callback"):
            return
        for hook, fn in (
            ("rect_on_click", self._on_rect_click),
            ("rect_on_drag", self._on_rect_drag),
            ("rect_on_drag_end", self._on_rect_drag_end),
            ("rect_on_resize_click", self._on_rect_resize_click),
            ("rect_on_resize_drag", self._on_rect_resize_drag),
            ("rect_on_resize_end", self._on_rect_resize_end),
        ):
            canvas.register_callback(hook, fn, "after")
            self._hook_callbacks.append((hook, fn, "after"))

    # -------------------------------------------------------------------------
    # Snap calculation (hot path — called at ~60 Hz during drag)
    # -------------------------------------------------------------------------

    def _get_effective_spacing(self, zoom: float) -> float:
        """Return the adaptive logical spacing for the current zoom level.

        Delegates to the linked :class:`CanvasGrid` when available so snap
        resolution always matches what is visually drawn.
        """
        if self._grid is not None:
            return self._grid._adaptive_spacing(self._grid._spacing, zoom)  # noqa: SLF001

        # Standalone: mirror CanvasGrid._adaptive_spacing logic exactly.
        effective = self._spacing
        px = effective * zoom

        for _ in range(_MAX_ADAPT_ITERS):
            if px >= _SNAP_DEFAULT_MIN_PX:
                break
            effective *= 2.0
            px *= 2.0

        for _ in range(_MAX_ADAPT_ITERS):
            if px <= _SNAP_DEFAULT_MAX_PX:
                break
            half_px = px * 0.5
            if half_px < _SNAP_DEFAULT_MIN_PX:
                break
            effective *= 0.5
            px = half_px

        return effective

    def _compute_snap_correction(self, cx: float, cy: float) -> tuple[float, float]:
        """Compute the (dx, dy) correction to snap the *ideal* canvas-space
        point (cx, cy) to the nearest grid line.

        The input must be the *ideal* position (unsnapped, tracking the real
        accumulated mouse delta).  Computing against the post-snap position
        causes the sticky-lock bug where the snap correction cancels every
        subsequent mouse delta.

        Returns ``(0.0, 0.0)`` when outside the snap threshold so callers can
        skip all canvas work with a cheap float comparison.

        Args:
            cx: Ideal canvas-space x of the snap anchor.
            cy: Ideal canvas-space y of the snap anchor.

        Returns:
            ``(corr_dx, corr_dy)`` in canvas-space pixels.
        """
        canvas = self._canvas
        zoom: float = getattr(canvas, "zoom_level", 1.0)
        ox: float = getattr(canvas, "_canvas_origin_x", 0.0)
        oy: float = getattr(canvas, "_canvas_origin_y", 0.0)

        eff_logical = self._get_effective_spacing(zoom)
        px_spacing = eff_logical * zoom
        if px_spacing <= 0.0:
            return 0.0, 0.0

        threshold_px = px_spacing * self._snap_ratio
        iz = 1.0 / zoom if zoom != 0.0 else 1.0

        corr_dx = 0.0
        corr_dy = 0.0

        if self._snap_x:
            logical_x = (cx - ox) * iz
            snapped_lx = round(logical_x / eff_logical) * eff_logical
            delta_x = snapped_lx * zoom + ox - cx
            if abs(delta_x) <= threshold_px:
                corr_dx = delta_x

        if self._snap_y:
            logical_y = (cy - oy) * iz
            snapped_ly = round(logical_y / eff_logical) * eff_logical
            delta_y = snapped_ly * zoom + oy - cy
            if abs(delta_y) <= threshold_px:
                corr_dy = delta_y

        return corr_dx, corr_dy

    # -------------------------------------------------------------------------
    # Hook callbacks — drag lifecycle
    # -------------------------------------------------------------------------

    def _on_rect_click(self, rect: Any, event: Any) -> None:
        """Record the drag origin so ideal-position tracking can begin."""
        if not self._enabled or not self._snap_move:
            return
        rc = self._canvas.coords(rect.rect)
        rid = id(rect)
        self._drag_click_mouse[rid] = (float(event.x), float(event.y))
        self._drag_click_rect[rid] = (rc[0], rc[1])

    def _on_rect_drag(self, rect: Any, event: Any) -> None:
        """After-hook for ``rect_on_drag`` — snap with ideal-position tracking.

        Computes the ideal TL (accumulated mouse delta from click origin),
        snaps it to the nearest grid line, then moves all selected objects from
        their current canvas position to the snapped target in one shot.
        """
        if not self._enabled or not self._snap_move:
            return

        canvas = self._canvas
        rid = id(rect)

        # Bootstrap: if snap was enabled after the click began, initialise now.
        if rid not in self._drag_click_mouse:
            rc = canvas.coords(rect.rect)
            self._drag_click_mouse[rid] = (float(event.x), float(event.y))
            self._drag_click_rect[rid] = (rc[0], rc[1])

        click_mx, click_my = self._drag_click_mouse[rid]
        start_x0, start_y0 = self._drag_click_rect[rid]

        # Ideal TL: where the rect would be if no snap correction had ever
        # been applied.  Uses widget-space delta (same coordinate system as
        # canvas.move) so it is invariant to panning and zoom.
        ideal_x0 = start_x0 + (event.x - click_mx)
        ideal_y0 = start_y0 + (event.y - click_my)

        # Snap correction relative to the ideal, not the post-snap position.
        corr_dx, corr_dy = self._compute_snap_correction(ideal_x0, ideal_y0)

        # Bring all selected objects from their current canvas pos to target.
        rc = canvas.coords(rect.rect)
        apply_dx = (ideal_x0 + corr_dx) - rc[0]
        apply_dy = (ideal_y0 + corr_dy) - rc[1]

        if apply_dx == 0.0 and apply_dy == 0.0:
            return

        selected = canvas.get_selected()
        for obj in selected:
            canvas.move(obj.rect, apply_dx, apply_dy)
            canvas.move(obj.resize_handle, apply_dx, apply_dy)
            if obj._has_move_attached:  # noqa: SLF001
                canvas.move_attached_items(obj, apply_dx, apply_dy)

    def _on_rect_drag_end(self, rect: Any, _event: Any) -> None:
        """Clear per-drag state on mouse release."""
        rid = id(rect)
        self._drag_click_mouse.pop(rid, None)
        self._drag_click_rect.pop(rid, None)

    # -------------------------------------------------------------------------
    # Hook callbacks — resize lifecycle
    # -------------------------------------------------------------------------

    def _on_rect_resize_click(self, rect: Any, event: Any) -> None:
        """Record the resize origin so ideal-position tracking can begin."""
        if not self._enabled or not self._snap_resize:
            return
        rc = self._canvas.coords(rect.rect)
        rid = id(rect)
        self._resize_click_mouse[rid] = (float(event.x), float(event.y))
        self._resize_click_rect[rid] = (rc[2], rc[3])

    def _on_rect_resize_drag(self, rect: Any, event: Any) -> None:
        """After-hook for ``rect_on_resize_drag`` — snap BR with ideal tracking.

        Mirrors ``_on_rect_drag`` but operates on the bottom-right corner
        (resize anchor).  Enforces minimum 1 px size on every selected rect so
        a snap correction can never produce a degenerate rectangle.
        """
        if not self._enabled or not self._snap_resize:
            return

        canvas = self._canvas
        rid = id(rect)

        # Bootstrap: initialise if resize-click was missed.
        if rid not in self._resize_click_mouse:
            rc = canvas.coords(rect.rect)
            self._resize_click_mouse[rid] = (float(event.x), float(event.y))
            self._resize_click_rect[rid] = (rc[2], rc[3])

        click_mx, click_my = self._resize_click_mouse[rid]
        start_x1, start_y1 = self._resize_click_rect[rid]

        ideal_x1 = start_x1 + (event.x - click_mx)
        ideal_y1 = start_y1 + (event.y - click_my)

        corr_dx, corr_dy = self._compute_snap_correction(ideal_x1, ideal_y1)

        rc = canvas.coords(rect.rect)
        apply_dx = (ideal_x1 + corr_dx) - rc[2]
        apply_dy = (ideal_y1 + corr_dy) - rc[3]

        if apply_dx == 0.0 and apply_dy == 0.0:
            return

        selected = canvas.get_selected()
        for obj in selected:
            cx0, cy0, cx1, cy1 = canvas.coords(obj.rect)
            new_x1 = cx1 + apply_dx
            new_y1 = cy1 + apply_dy
            # Enforce minimum size so snap can never produce an inverted rect.
            if new_x1 <= cx0:
                new_x1 = cx0 + 1.0
            if new_y1 <= cy0:
                new_y1 = cy0 + 1.0
            canvas.coords(obj.rect, cx0, cy0, new_x1, new_y1)
            canvas.coords(obj.resize_handle, new_x1, new_y1)

        # Flag that objects changed so history saves on ButtonRelease.
        if hasattr(canvas, "_objects_changed"):
            canvas._objects_changed = True  # noqa: SLF001

    def _on_rect_resize_end(self, rect: Any, _event: Any) -> None:
        """Clear per-resize state on mouse release."""
        rid = id(rect)
        self._resize_click_mouse.pop(rid, None)
        self._resize_click_rect.pop(rid, None)
