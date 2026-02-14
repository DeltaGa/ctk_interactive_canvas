"""
Draggable Rectangle Component for CustomTkinter Canvas

Provides resizable, draggable rectangles with alignment/distribution features,
unit conversion (mm/px), keyboard modifier support, and comprehensive magic
methods for intuitive mathematical operations.

Author: Tchicdje Kouojip Joram Smith (DeltaGa)
Enhanced: Dave Erickson
"""

import logging
import math
import weakref
from typing import TYPE_CHECKING, Any, Iterator, List, Optional, Tuple, Union

if TYPE_CHECKING:
    from tkinter import Event

    from .interactive_canvas import InteractiveCanvas


class KeyboardStateManager:
    """Manages keyboard modifier state per canvas instance."""

    def __init__(self) -> None:
        """Initialize keyboard state tracking."""
        self.shift_held: bool = False
        self.alt_held: bool = False
        self.ctrl_held: bool = False

    def on_shift_press(self, event: "Event") -> None:
        """Handle Shift key press."""
        self.shift_held = True

    def on_shift_release(self, event: "Event") -> None:
        """Handle Shift key release."""
        self.shift_held = False

    def on_alt_press(self, event: "Event") -> None:
        """Handle Alt key press."""
        self.alt_held = True

    def on_alt_release(self, event: "Event") -> None:
        """Handle Alt key release."""
        self.alt_held = False

    def on_ctrl_press(self, event: "Event") -> None:
        """Handle Ctrl key press."""
        self.ctrl_held = True

    def on_ctrl_release(self, event: "Event") -> None:
        """Handle Ctrl key release."""
        self.ctrl_held = False


class DraggableRectangle:
    """
    A draggable and resizable rectangle on a CustomTkinter canvas.

    Supports intuitive mathematical operations:
        rect + [dx, dy]     : Translate by offset (returns new rectangle)
        rect - [dx, dy]     : Translate by negative offset
        rect * scalar       : Scale size from center
        rect / scalar       : Scale size down from center
        rect += [dx, dy]    : Translate in place
        rect *= scalar      : Scale in place
        [x, y] in rect      : Check if point is inside rectangle
        rect1 == rect2      : Compare position and size
        rect1 < rect2       : Compare by area
        len(rect)           : Returns 4 (x0, y0, x1, y1)
        rect[i]             : Access coordinates by index
        iter(rect)          : Iterate over coordinates
        bool(rect)          : True if non-zero area
        rect1 & rect2       : Intersection rectangle
        rect1 | rect2       : Bounding rectangle (union)

    Features:
        - Drag to move
        - Resize handle in bottom-right corner
        - Shift key: Constrain movement to horizontal/vertical
        - Shift key during resize: Maintain aspect ratio
        - Alt key during resize: Resize in one dimension only
        - Unit conversion between pixels and millimeters
        - Class methods for alignment and distribution
    """

    _instances: List[weakref.ref] = []
    ALIGN_MODES = ["top", "middle", "bottom", "start", "center", "end"]
    DISTRIBUTE_MODES = ["horizontal", "vertical"]

    def __init__(
        self,
        canvas: "InteractiveCanvas",
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        dpi: int = 300,
        radius: int = 5,
        **kwargs: Any,
    ) -> None:
        """
        Initialize a draggable rectangle.

        Args:
            canvas: The parent InteractiveCanvas instance.
            x1: Top-left x coordinate.
            y1: Top-left y coordinate.
            x2: Bottom-right x coordinate.
            y2: Bottom-right y coordinate.
            dpi: Dots per inch for unit conversion (default: 300).
            radius: Radius of the resize handle circle (default: 5).
            **kwargs: Additional arguments passed to canvas.create_rectangle.
        """
        self.canvas = canvas
        self.dpi = dpi
        self.is_selected = False
        self.original_outline = kwargs.get("outline", "black")

        self.rect = canvas.create_rectangle(x1, y1, x2, y2, **kwargs)
        self.resize_handle = canvas.create_aa_circle(x2, y2, radius=radius, fill="#00497b")

        if not hasattr(canvas, "_keyboard_state"):
            canvas._keyboard_state = KeyboardStateManager()
            canvas.bind_all("<Shift_L>", canvas._keyboard_state.on_shift_press)
            canvas.bind_all("<KeyRelease-Shift_L>", canvas._keyboard_state.on_shift_release)
            canvas.bind_all("<Alt_L>", canvas._keyboard_state.on_alt_press)
            canvas.bind_all("<KeyRelease-Alt_L>", canvas._keyboard_state.on_alt_release)
            canvas.bind_all("<Control_L>", canvas._keyboard_state.on_ctrl_press)
            canvas.bind_all("<KeyRelease-Control_L>", canvas._keyboard_state.on_ctrl_release)

        self.keyboard_state = canvas._keyboard_state

        self.canvas.tag_bind(self.rect, "<Button-1>", self.on_click)
        self.canvas.tag_bind(self.rect, "<B1-Motion>", self.on_drag)
        self.canvas.tag_bind(self.resize_handle, "<Button-1>", self.on_resize_click)
        self.canvas.tag_bind(self.resize_handle, "<B1-Motion>", self.on_resize_drag)

        self._self_ref = weakref.ref(self)
        self.__class__._instances.append(self._self_ref)

    def __repr__(self) -> str:
        """
        Developer-friendly representation.

        Returns:
            String representation suitable for debugging and logging.
        """
        x0, y0, x1, y1 = self.canvas.coords(self.rect)
        return (
            f"DraggableRectangle(canvas={id(self.canvas):#x}, "
            f"x1={x0:.1f}, y1={y0:.1f}, x2={x1:.1f}, y2={y1:.1f}, "
            f"dpi={self.dpi})"
        )

    def __str__(self) -> str:
        """
        User-friendly string representation.

        Returns:
            Human-readable string showing position and size.
        """
        x0, y0, x1, y1 = self.canvas.coords(self.rect)
        width, height = x1 - x0, y1 - y0
        return f"Rectangle(pos=[{x0:.1f}, {y0:.1f}], size=[{width:.1f}, {height:.1f}])"

    def __format__(self, format_spec: str) -> str:
        """
        Custom format support for f-strings.

        Args:
            format_spec: Format specification
                's' or '' - String representation (default)
                'r' - repr representation
                'c' - Comma-separated coordinates
                'p' - Point notation

        Returns:
            Formatted string representation.
        """
        if not format_spec or format_spec == "s":
            return str(self)
        elif format_spec == "r":
            return repr(self)
        elif format_spec == "c":
            return f"[{', '.join(f'{c:.1f}' for c in self.canvas.coords(self.rect))}]"
        elif format_spec == "p":
            x0, y0, x1, y1 = self.canvas.coords(self.rect)
            return f"({x0:.1f}, {y0:.1f}) -> ({x1:.1f}, {y1:.1f})"
        else:
            return str(self)

    def __bool__(self) -> bool:
        """
        Truthiness check based on non-zero area.

        Returns:
            True if rectangle has positive width and height, False otherwise.
        """
        coords = self.canvas.coords(self.rect)
        x0, y0, x1, y1 = float(coords[0]), float(coords[1]), float(coords[2]), float(coords[3])
        return (x1 - x0) > 0 and (y1 - y0) > 0

    def __len__(self) -> int:
        """
        Number of coordinate values.

        Returns:
            Always returns 4 (x0, y0, x1, y1).
        """
        return 4

    def __getitem__(self, index: Union[int, slice]) -> Union[float, List[float]]:
        """
        Access coordinates by index or slice.

        Args:
            index: Integer index (0-3) or slice object
                0: x0 (top-left x)
                1: y0 (top-left y)
                2: x1 (bottom-right x)
                3: y1 (bottom-right y)

        Returns:
            Single coordinate value or list of values for slices.

        Raises:
            TypeError: If index is not int or slice.
            IndexError: If index is out of range.
        """
        coords_tuple = self.canvas.coords(self.rect)
        coords: List[float] = [float(c) for c in coords_tuple]
        if isinstance(index, slice):
            return coords[index]
        if not isinstance(index, int):
            raise TypeError(f"indices must be integers or slices, not {type(index).__name__}")
        if index < -4 or index >= 4:
            raise IndexError("rectangle index out of range")
        return float(coords[index])

    def __setitem__(self, index: int, value: float) -> None:
        """
        Modify a coordinate by index.

        Args:
            index: Coordinate index (0-3)
            value: New coordinate value

        Raises:
            TypeError: If index is not an integer.
            IndexError: If index is out of range.
            ValueError: If new coordinates would be invalid (x1 <= x0 or y1 <= y0).
        """
        if not isinstance(index, int):
            raise TypeError(f"indices must be integers, not {type(index).__name__}")
        if index < -4 or index >= 4:
            raise IndexError("rectangle index out of range")

        coords = list(self.canvas.coords(self.rect))
        coords[index] = value

        x0, y0, x1, y1 = coords
        if x1 <= x0 or y1 <= y0:
            raise ValueError("invalid coordinates: x1 must be > x0 and y1 must be > y0")

        self.canvas.coords(self.rect, x0, y0, x1, y1)
        self.canvas.coords(self.resize_handle, x1, y1)

    def __iter__(self) -> Iterator[float]:
        """
        Iterate over coordinates.

        Returns:
            Iterator yielding x0, y0, x1, y1 in sequence.
        """
        return iter(self.canvas.coords(self.rect))

    def __contains__(self, point: Union[List[float], Tuple[float, float]]) -> bool:
        """
        Check if a point is inside the rectangle.

        Args:
            point: [x, y] coordinates or (x, y) tuple

        Returns:
            True if point is within or on the boundary, False otherwise.

        Raises:
            TypeError: If point is not a two-element sequence.
        """
        if not isinstance(point, (list, tuple)) or len(point) != 2:
            raise TypeError("point must be a sequence of two numbers [x, y]")

        x, y = point
        coords = self.canvas.coords(self.rect)
        x0, y0, x1, y1 = float(coords[0]), float(coords[1]), float(coords[2]), float(coords[3])
        return bool(x0 <= x <= x1 and y0 <= y <= y1)

    def __eq__(self, other: object) -> bool:
        """
        Equality comparison based on coordinates.

        Args:
            other: Another DraggableRectangle instance

        Returns:
            True if coordinates match within 1e-9 tolerance, False otherwise.
        """
        if not isinstance(other, DraggableRectangle):
            return NotImplemented

        self_coords = self.canvas.coords(self.rect)
        other_coords = other.canvas.coords(other.rect)

        return all(abs(a - b) < 1e-9 for a, b in zip(self_coords, other_coords))

    def __ne__(self, other: object) -> bool:
        """
        Inequality comparison.

        Args:
            other: Another DraggableRectangle instance

        Returns:
            True if coordinates differ, False otherwise.
        """
        result = self.__eq__(other)
        if result is NotImplemented:
            return result
        return not result

    def __lt__(self, other: Any) -> bool:
        """
        Less-than comparison based on area.

        Args:
            other: Another DraggableRectangle instance

        Returns:
            True if this rectangle's area is smaller.
        """
        if not isinstance(other, DraggableRectangle):
            return NotImplemented
        return self._area() < other._area()

    def __le__(self, other: Any) -> bool:
        """
        Less-than-or-equal comparison based on area.

        Args:
            other: Another DraggableRectangle instance

        Returns:
            True if this rectangle's area is smaller or equal.
        """
        if not isinstance(other, DraggableRectangle):
            return NotImplemented
        return self._area() <= other._area()

    def __gt__(self, other: Any) -> bool:
        """
        Greater-than comparison based on area.

        Args:
            other: Another DraggableRectangle instance

        Returns:
            True if this rectangle's area is larger.
        """
        if not isinstance(other, DraggableRectangle):
            return NotImplemented
        return self._area() > other._area()

    def __ge__(self, other: Any) -> bool:
        """
        Greater-than-or-equal comparison based on area.

        Args:
            other: Another DraggableRectangle instance

        Returns:
            True if this rectangle's area is larger or equal.
        """
        if not isinstance(other, DraggableRectangle):
            return NotImplemented
        return self._area() >= other._area()

    def __hash__(self) -> int:
        """
        Hash value for use in sets and dictionaries.

        Returns:
            Integer hash based on rounded coordinates.
        """
        coords = tuple(round(c, 6) for c in self.canvas.coords(self.rect))
        return hash(coords)

    def __add__(self, offset: Union[List[float], Tuple[float, float]]) -> "DraggableRectangle":
        """
        Translate rectangle by offset (returns new rectangle).

        Args:
            offset: [dx, dy] translation vector

        Returns:
            New DraggableRectangle at translated position.

        Raises:
            TypeError: If offset is not a two-element sequence.
        """
        if not isinstance(offset, (list, tuple)) or len(offset) != 2:
            raise TypeError("offset must be a sequence of two numbers [dx, dy]")

        dx, dy = offset
        x0, y0, x1, y1 = self.canvas.coords(self.rect)

        return DraggableRectangle(
            self.canvas,
            x0 + dx,
            y0 + dy,
            x1 + dx,
            y1 + dy,
            dpi=self.dpi,
            outline=self.original_outline,
        )

    def __radd__(self, offset: Union[List[float], Tuple[float, float]]) -> "DraggableRectangle":
        """
        Right-hand addition (commutative).

        Args:
            offset: [dx, dy] translation vector

        Returns:
            New DraggableRectangle at translated position.
        """
        return self.__add__(offset)

    def __sub__(self, offset: Union[List[float], Tuple[float, float]]) -> "DraggableRectangle":
        """
        Translate rectangle by negative offset (returns new rectangle).

        Args:
            offset: [dx, dy] translation vector to subtract

        Returns:
            New DraggableRectangle at translated position.

        Raises:
            TypeError: If offset is not a two-element sequence.
        """
        if not isinstance(offset, (list, tuple)) or len(offset) != 2:
            raise TypeError("offset must be a sequence of two numbers [dx, dy]")

        dx, dy = offset
        return self.__add__([-dx, -dy])

    def __rsub__(self, offset: Union[List[float], Tuple[float, float]]) -> "DraggableRectangle":
        """
        Right-hand subtraction (offset - rect).

        Args:
            offset: [x, y] origin point

        Returns:
            New DraggableRectangle with coordinates relative to offset.

        Raises:
            TypeError: If offset is not a two-element sequence.
        """
        if not isinstance(offset, (list, tuple)) or len(offset) != 2:
            raise TypeError("offset must be a sequence of two numbers [dx, dy]")

        dx, dy = offset
        x0, y0, x1, y1 = self.canvas.coords(self.rect)

        return DraggableRectangle(
            self.canvas,
            dx - x0,
            dy - y0,
            dx + (x1 - x0),
            dy + (y1 - y0),
            dpi=self.dpi,
            outline=self.original_outline,
        )

    def __mul__(self, scalar: Union[int, float]) -> "DraggableRectangle":
        """
        Scale rectangle size from center (returns new rectangle).

        Args:
            scalar: Scaling factor (must be non-negative)

        Returns:
            New DraggableRectangle with scaled size, centered at same point.

        Raises:
            TypeError: If scalar is not numeric.
            ValueError: If scalar is negative.
        """
        if not isinstance(scalar, (int, float)):
            raise TypeError(
                f"unsupported operand type for *: 'DraggableRectangle' and '{type(scalar).__name__}'"
            )
        if scalar < 0:
            raise ValueError("scaling factor must be non-negative")

        x0, y0, x1, y1 = self.canvas.coords(self.rect)
        center_x, center_y = (x0 + x1) / 2, (y0 + y1) / 2
        half_width, half_height = (x1 - x0) / 2, (y1 - y0) / 2

        new_half_width = half_width * scalar
        new_half_height = half_height * scalar

        return DraggableRectangle(
            self.canvas,
            center_x - new_half_width,
            center_y - new_half_height,
            center_x + new_half_width,
            center_y + new_half_height,
            dpi=self.dpi,
            outline=self.original_outline,
        )

    def __rmul__(self, scalar: Union[int, float]) -> "DraggableRectangle":
        """
        Right-hand multiplication (commutative).

        Args:
            scalar: Scaling factor

        Returns:
            New scaled DraggableRectangle.
        """
        return self.__mul__(scalar)

    def __truediv__(self, scalar: Union[int, float]) -> "DraggableRectangle":
        """
        Scale rectangle size down (divide) from center.

        Args:
            scalar: Division factor (must be non-zero and positive)

        Returns:
            New DraggableRectangle with size divided by scalar.

        Raises:
            TypeError: If scalar is not numeric.
            ZeroDivisionError: If scalar is zero.
            ValueError: If scalar is negative.
        """
        if not isinstance(scalar, (int, float)):
            raise TypeError(
                f"unsupported operand type for /: 'DraggableRectangle' and '{type(scalar).__name__}'"
            )
        if scalar == 0:
            raise ZeroDivisionError("cannot divide rectangle by zero")
        if scalar < 0:
            raise ValueError("scaling factor must be non-negative")

        return self.__mul__(1 / scalar)

    def __floordiv__(self, scalar: Union[int, float]) -> "DraggableRectangle":
        """
        Integer division scaling from center.

        Args:
            scalar: Division factor

        Returns:
            New DraggableRectangle with integer-scaled size.

        Raises:
            TypeError: If scalar is not numeric.
            ZeroDivisionError: If scalar is zero.
            ValueError: If scalar is negative.
        """
        if not isinstance(scalar, (int, float)):
            raise TypeError(
                f"unsupported operand type for //: 'DraggableRectangle' and '{type(scalar).__name__}'"
            )
        if scalar == 0:
            raise ZeroDivisionError("cannot divide rectangle by zero")
        if scalar < 0:
            raise ValueError("scaling factor must be non-negative")

        return self.__mul__(1 // scalar if isinstance(scalar, int) else int(1 / scalar))

    def __iadd__(self, offset: Union[List[float], Tuple[float, float]]) -> "DraggableRectangle":
        """
        Translate rectangle in-place (modifies this rectangle).

        Args:
            offset: [dx, dy] translation vector

        Returns:
            Self (for chaining).

        Raises:
            TypeError: If offset is not a two-element sequence.
        """
        if not isinstance(offset, (list, tuple)) or len(offset) != 2:
            raise TypeError("offset must be a sequence of two numbers [dx, dy]")

        dx, dy = offset
        self.canvas.move(self.rect, dx, dy)
        self.canvas.move(self.resize_handle, dx, dy)
        return self

    def __isub__(self, offset: Union[List[float], Tuple[float, float]]) -> "DraggableRectangle":
        """
        Translate rectangle in-place by negative offset.

        Args:
            offset: [dx, dy] translation vector to subtract

        Returns:
            Self (for chaining).

        Raises:
            TypeError: If offset is not a two-element sequence.
        """
        if not isinstance(offset, (list, tuple)) or len(offset) != 2:
            raise TypeError("offset must be a sequence of two numbers [dx, dy]")

        dx, dy = offset
        return self.__iadd__([-dx, -dy])

    def __imul__(self, scalar: Union[int, float]) -> "DraggableRectangle":
        """
        Scale rectangle in-place from center.

        Args:
            scalar: Scaling factor (must be non-negative)

        Returns:
            Self (for chaining).

        Raises:
            TypeError: If scalar is not numeric.
            ValueError: If scalar is negative.
        """
        if not isinstance(scalar, (int, float)):
            raise TypeError(
                f"unsupported operand type for *=: 'DraggableRectangle' and '{type(scalar).__name__}'"
            )
        if scalar < 0:
            raise ValueError("scaling factor must be non-negative")

        x0, y0, x1, y1 = self.canvas.coords(self.rect)
        center_x, center_y = (x0 + x1) / 2, (y0 + y1) / 2
        half_width, half_height = (x1 - x0) / 2, (y1 - y0) / 2

        new_half_width = half_width * scalar
        new_half_height = half_height * scalar

        new_x0 = center_x - new_half_width
        new_y0 = center_y - new_half_height
        new_x1 = center_x + new_half_width
        new_y1 = center_y + new_half_height

        self.canvas.coords(self.rect, new_x0, new_y0, new_x1, new_y1)
        self.canvas.coords(self.resize_handle, new_x1, new_y1)
        return self

    def __itruediv__(self, scalar: Union[int, float]) -> "DraggableRectangle":
        """
        Scale rectangle in-place (divide size).

        Args:
            scalar: Division factor (must be non-zero and positive)

        Returns:
            Self (for chaining).

        Raises:
            TypeError: If scalar is not numeric.
            ZeroDivisionError: If scalar is zero.
            ValueError: If scalar is negative.
        """
        if not isinstance(scalar, (int, float)):
            raise TypeError(
                f"unsupported operand type for /=: 'DraggableRectangle' and '{type(scalar).__name__}'"
            )
        if scalar == 0:
            raise ZeroDivisionError("cannot divide rectangle by zero")
        if scalar < 0:
            raise ValueError("scaling factor must be non-negative")

        return self.__imul__(1 / scalar)

    def __and__(self, other: "DraggableRectangle") -> Optional["DraggableRectangle"]:
        """
        Rectangle intersection (geometric AND).

        Args:
            other: Another DraggableRectangle

        Returns:
            New DraggableRectangle representing intersection, or None if no overlap.

        Raises:
            TypeError: If other is not a DraggableRectangle.
        """
        if not isinstance(other, DraggableRectangle):
            raise TypeError(
                f"unsupported operand type for &: 'DraggableRectangle' and '{type(other).__name__}'"
            )

        x0_a, y0_a, x1_a, y1_a = self.canvas.coords(self.rect)
        x0_b, y0_b, x1_b, y1_b = other.canvas.coords(other.rect)

        x0_i = max(x0_a, x0_b)
        y0_i = max(y0_a, y0_b)
        x1_i = min(x1_a, x1_b)
        y1_i = min(y1_a, y1_b)

        if x0_i >= x1_i or y0_i >= y1_i:
            return None

        return DraggableRectangle(
            self.canvas, x0_i, y0_i, x1_i, y1_i, dpi=self.dpi, outline=self.original_outline
        )

    def __or__(self, other: "DraggableRectangle") -> "DraggableRectangle":
        """
        Bounding rectangle (geometric OR/union).

        Args:
            other: Another DraggableRectangle

        Returns:
            New DraggableRectangle that contains both rectangles.

        Raises:
            TypeError: If other is not a DraggableRectangle.
        """
        if not isinstance(other, DraggableRectangle):
            raise TypeError(
                f"unsupported operand type for |: 'DraggableRectangle' and '{type(other).__name__}'"
            )

        x0_a, y0_a, x1_a, y1_a = self.canvas.coords(self.rect)
        x0_b, y0_b, x1_b, y1_b = other.canvas.coords(other.rect)

        x0_u = min(x0_a, x0_b)
        y0_u = min(y0_a, y0_b)
        x1_u = max(x1_a, x1_b)
        y1_u = max(y1_a, y1_b)

        return DraggableRectangle(
            self.canvas, x0_u, y0_u, x1_u, y1_u, dpi=self.dpi, outline=self.original_outline
        )

    def __neg__(self) -> "DraggableRectangle":
        """
        Negate coordinates (reflection through origin).

        Returns:
            New DraggableRectangle with negated coordinates.
        """
        x0, y0, x1, y1 = self.canvas.coords(self.rect)
        return DraggableRectangle(
            self.canvas, -x1, -y1, -x0, -y0, dpi=self.dpi, outline=self.original_outline
        )

    def __pos__(self) -> "DraggableRectangle":
        """
        Identity operation (returns copy).

        Returns:
            New DraggableRectangle with same coordinates.
        """
        x0, y0, x1, y1 = self.canvas.coords(self.rect)
        return DraggableRectangle(
            self.canvas, x0, y0, x1, y1, dpi=self.dpi, outline=self.original_outline
        )

    def __abs__(self) -> "DraggableRectangle":
        """
        Absolute value of coordinates.

        Returns:
            New DraggableRectangle with absolute coordinates.
        """
        x0, y0, x1, y1 = self.canvas.coords(self.rect)
        return DraggableRectangle(
            self.canvas,
            abs(x0),
            abs(y0),
            abs(x1),
            abs(y1),
            dpi=self.dpi,
            outline=self.original_outline,
        )

    def _area(self) -> float:
        """
        Calculate rectangle area.

        Returns:
            Area in square pixels.
        """
        coords = self.canvas.coords(self.rect)
        x0, y0, x1, y1 = float(coords[0]), float(coords[1]), float(coords[2]), float(coords[3])
        return (x1 - x0) * (y1 - y0)

    def delete(self) -> None:
        """Delete this rectangle from canvas and remove from instance tracking."""
        self.canvas.delete(self.rect)
        self.canvas.delete(self.resize_handle)

        if self._self_ref in self.__class__._instances:
            self.__class__._instances.remove(self._self_ref)

    @classmethod
    def get_instances(cls) -> List["DraggableRectangle"]:
        """Get all currently alive DraggableRectangle instances."""
        cls._instances = [ref for ref in cls._instances if ref() is not None]
        return [instance for ref in cls._instances if (instance := ref()) is not None]

    def set_topleft_pos(
        self,
        new_pos: List[float],
        relative_pos: Optional[List[float]] = None,
        in_mm: bool = False,
        dpi: Optional[int] = None,
    ) -> None:
        """
        Set the top-left position of the rectangle.

        Args:
            new_pos: [x, y] coordinates for new top-left position.
            relative_pos: Optional [dx, dy] offset to add.
            in_mm: Whether new_pos is in millimeters (converts to pixels).
            dpi: DPI for conversion (uses self.dpi if not specified).
        """
        if dpi is None:
            dpi = self.dpi

        if in_mm:
            new_pos = [self.convert_mm_to_px(pos, dpi) for pos in new_pos]

        if relative_pos is not None:
            new_pos = [new_pos[0] + relative_pos[0], new_pos[1] + relative_pos[1]]

        coords_tuple = self.canvas.coords(self.rect)
        if coords_tuple is None:
            return
        x0, y0, x1, y1 = coords_tuple
        dx = new_pos[0] - x0
        dy = new_pos[1] - y0

        self.canvas.move(self.rect, dx, dy)
        self.canvas.move(self.resize_handle, dx, dy)

    def set_bottomright_pos(
        self,
        new_pos: List[float],
        relative_pos: Optional[List[float]] = None,
        in_mm: bool = False,
        dpi: Optional[int] = None,
    ) -> None:
        """
        Set the bottom-right position of the rectangle (resize operation).

        Args:
            new_pos: [x, y] coordinates for new bottom-right position.
            relative_pos: Optional [dx, dy] offset to add.
            in_mm: Whether new_pos is in millimeters (converts to pixels).
            dpi: DPI for conversion (uses self.dpi if not specified).
        """
        if dpi is None:
            dpi = self.dpi

        if in_mm:
            new_pos = [self.convert_mm_to_px(pos, dpi) for pos in new_pos]

        if relative_pos is not None:
            new_pos = [new_pos[0] + relative_pos[0], new_pos[1] + relative_pos[1]]

        coords_tuple = self.canvas.coords(self.rect)
        if coords_tuple is None:
            return
        x0, y0, _, _ = coords_tuple
        self.canvas.coords(self.rect, x0, y0, new_pos[0], new_pos[1])
        self.canvas.coords(self.resize_handle, new_pos[0], new_pos[1])

    def set_size(
        self, new_size: List[float], in_mm: bool = False, dpi: Optional[int] = None
    ) -> None:
        """
        Set the size of the rectangle.

        Args:
            new_size: [width, height] dimensions.
            in_mm: Whether new_size is in millimeters (converts to pixels).
            dpi: DPI for conversion (uses self.dpi if not specified).
        """
        if dpi is None:
            dpi = self.dpi

        if in_mm:
            new_size = [self.convert_mm_to_px(size, dpi) for size in new_size]

        coords_tuple = self.canvas.coords(self.rect)
        if coords_tuple is None:
            return
        x0, y0, _, _ = coords_tuple
        self.canvas.coords(self.rect, x0, y0, x0 + new_size[0], y0 + new_size[1])
        self.canvas.coords(self.resize_handle, x0 + new_size[0], y0 + new_size[1])

    def get_topleft_pos(
        self,
        relative_pos: Optional[List[float]] = None,
        in_mm: bool = False,
        dpi: Optional[int] = None,
    ) -> List[float]:
        """
        Get the top-left position of the rectangle.

        Args:
            relative_pos: Optional [dx, dy] offset to subtract.
            in_mm: Whether to return in millimeters instead of pixels.
            dpi: DPI for conversion (uses self.dpi if not specified).

        Returns:
            [x, y] coordinates of top-left corner.
        """
        if dpi is None:
            dpi = self.dpi

        coords_tuple = self.canvas.coords(self.rect)
        if coords_tuple is None:
            return [0.0, 0.0]
        x0, y0, _, _ = coords_tuple

        if relative_pos is not None:
            x0 -= relative_pos[0]
            y0 -= relative_pos[1]

        if in_mm:
            x0 = self.convert_px_to_mm(x0, dpi)
            y0 = self.convert_px_to_mm(y0, dpi)

        return [x0, y0]

    def get_bottomright_pos(
        self,
        relative_pos: Optional[List[float]] = None,
        in_mm: bool = False,
        dpi: Optional[int] = None,
    ) -> List[float]:
        """
        Get the bottom-right position of the rectangle.

        Args:
            relative_pos: Optional [dx, dy] offset to subtract.
            in_mm: Whether to return in millimeters instead of pixels.
            dpi: DPI for conversion (uses self.dpi if not specified).

        Returns:
            [x, y] coordinates of bottom-right corner.
        """
        if dpi is None:
            dpi = self.dpi

        coords_tuple = self.canvas.coords(self.rect)
        if coords_tuple is None:
            return [0.0, 0.0]
        _, _, x1, y1 = coords_tuple

        if relative_pos is not None:
            x1 -= relative_pos[0]
            y1 -= relative_pos[1]

        if in_mm:
            x1 = self.convert_px_to_mm(x1, dpi)
            y1 = self.convert_px_to_mm(y1, dpi)

        return [x1, y1]

    def get_size(self, in_mm: bool = False, dpi: Optional[int] = None) -> List[float]:
        """
        Get the size of the rectangle.

        Args:
            in_mm: Whether to return in millimeters instead of pixels.
            dpi: DPI for conversion (uses self.dpi if not specified).

        Returns:
            [width, height] dimensions.
        """
        if dpi is None:
            dpi = self.dpi

        coords_tuple = self.canvas.coords(self.rect)
        if coords_tuple is None:
            return [0.0, 0.0]
        x0, y0, x1, y1 = coords_tuple
        width = x1 - x0
        height = y1 - y0

        if in_mm:
            width = self.convert_px_to_mm(width, dpi)
            height = self.convert_px_to_mm(height, dpi)

        return [width, height]

    def safe_rotate(self, angle: int, anchor: str = "topleft") -> None:
        """
        Rotate the rectangle by swapping dimensions (90/180/-90/-180 degrees).

        Args:
            angle: Rotation angle (must be 90, 180, -90, or -180).
            anchor: Anchor point for rotation (topleft, topright, bottomleft, bottomright, or center).

        Raises:
            ValueError: If angle or anchor is invalid.
        """
        if angle not in [90, 180, -90, -180]:
            raise ValueError("Angle must be one of [90, 180, -90, -180]")
        if anchor not in ["topleft", "topright", "bottomleft", "bottomright", "center"]:
            raise ValueError(
                "Anchor must be one of ['topleft', 'topright', 'bottomleft', "
                "'bottomright', 'center']"
            )

        x0, y0, x1, y1 = self.canvas.coords(self.rect)
        width = x1 - x0
        height = y1 - y0

        if angle in [90, -90]:
            width, height = height, width

        if anchor == "topleft":
            new_x0, new_y0 = x0, y0
            new_x1, new_y1 = x0 + width, y0 + height
        elif anchor == "topright":
            new_x0, new_y0 = x1 - width, y0
            new_x1, new_y1 = x1, y0 + height
        elif anchor == "bottomleft":
            new_x0, new_y0 = x0, y1 - height
            new_x1, new_y1 = x0 + width, y1
        elif anchor == "bottomright":
            new_x0, new_y0 = x1 - width, y1 - height
            new_x1, new_y1 = x1, y1
        elif anchor == "center":
            center_x = (x0 + x1) / 2
            center_y = (y0 + y1) / 2
            new_x0 = center_x - width / 2
            new_y0 = center_y - height / 2
            new_x1 = center_x + width / 2
            new_y1 = center_y + height / 2

        self.canvas.coords(self.rect, new_x0, new_y0, new_x1, new_y1)
        self.canvas.coords(self.resize_handle, new_x1, new_y1)

    @classmethod
    def align(
        cls,
        rectangles: List["DraggableRectangle"],
        mode: str,
        relative_pos: Optional[List[float]] = None,
    ) -> None:
        """
        Align multiple rectangles relative to the first rectangle.

        Args:
            rectangles: List of rectangles to align.
            mode: Alignment mode (top, middle, bottom, start, center, end).
            relative_pos: Optional canvas origin offset for coordinate calculations.

        Raises:
            ValueError: If mode is invalid.
        """
        if mode not in cls.ALIGN_MODES:
            raise ValueError(f"Invalid alignment mode: {mode}. Must be one of {cls.ALIGN_MODES}")
        if not rectangles:
            return

        canvas_origin = relative_pos if relative_pos is not None else [0, 0]
        first_rect = rectangles[0]
        x1, y1 = first_rect.get_topleft_pos(relative_pos=canvas_origin)

        for rect in rectangles:
            if mode == "top":
                x = rect.get_topleft_pos(relative_pos=canvas_origin)[0]
                y = y1
            elif mode == "middle":
                x = rect.get_topleft_pos(relative_pos=canvas_origin)[0]
                y = y1 + (first_rect.get_size()[1] // 2) - (rect.get_size()[1] // 2)
            elif mode == "bottom":
                x = rect.get_topleft_pos(relative_pos=canvas_origin)[0]
                y = y1 + first_rect.get_size()[1] - rect.get_size()[1]
            elif mode == "start":
                x = x1
                y = rect.get_topleft_pos(relative_pos=canvas_origin)[1]
            elif mode == "center":
                x = x1 + (first_rect.get_size()[0] // 2) - (rect.get_size()[0] // 2)
                y = rect.get_topleft_pos(relative_pos=canvas_origin)[1]
            elif mode == "end":
                x = x1 + first_rect.get_size()[0] - rect.get_size()[0]
                y = rect.get_topleft_pos(relative_pos=canvas_origin)[1]

            rect.set_topleft_pos([x, y], relative_pos=canvas_origin)

    @classmethod
    def distribute(
        cls,
        rectangles: List["DraggableRectangle"],
        mode: str,
        relative_pos: Optional[List[float]] = None,
    ) -> None:
        """
        Distribute multiple rectangles evenly with equal spacing.

        Args:
            rectangles: List of rectangles to distribute (must be 2+).
            mode: Distribution mode (horizontal or vertical).
            relative_pos: Optional canvas origin offset for coordinate calculations.

        Raises:
            ValueError: If mode is invalid.
        """
        if mode not in cls.DISTRIBUTE_MODES:
            raise ValueError(
                f"Invalid distribution mode: {mode}. Must be one of {cls.DISTRIBUTE_MODES}"
            )
        if not rectangles or len(rectangles) < 2:
            return

        canvas_origin = relative_pos if relative_pos is not None else [0, 0]

        if mode == "horizontal":
            rectangles.sort(key=lambda r: r.get_topleft_pos(relative_pos=canvas_origin)[0])
            total_width = sum(rect.get_size()[0] for rect in rectangles)
            first_x = rectangles[0].get_topleft_pos(relative_pos=canvas_origin)[0]
            last_x = rectangles[-1].get_topleft_pos(relative_pos=canvas_origin)[0]
            total_space = last_x - first_x
            space_between = (total_space - total_width) // (len(rectangles) - 1)

            x = first_x
            for rect in rectangles:
                current_y = rect.get_topleft_pos(relative_pos=canvas_origin)[1]
                rect.set_topleft_pos([x, current_y], relative_pos=canvas_origin)
                x += rect.get_size()[0] + space_between

        elif mode == "vertical":
            rectangles.sort(key=lambda r: r.get_topleft_pos(relative_pos=canvas_origin)[1])
            total_height = sum(rect.get_size()[1] for rect in rectangles)
            first_y = rectangles[0].get_topleft_pos(relative_pos=canvas_origin)[1]
            last_y = rectangles[-1].get_topleft_pos(relative_pos=canvas_origin)[1]
            total_space = last_y - first_y
            space_between = (total_space - total_height) // (len(rectangles) - 1)

            y = first_y
            for rect in rectangles:
                current_x = rect.get_topleft_pos(relative_pos=canvas_origin)[0]
                rect.set_topleft_pos([current_x, y], relative_pos=canvas_origin)
                y += rect.get_size()[1] + space_between

    def copy_(self, offset: Optional[List[float]] = None, **kwargs: Any) -> "DraggableRectangle":
        """
        Create a copy of this rectangle at an offset position.

        Args:
            offset: [dx, dy] offset for the copy (default: [50, 50]).
            **kwargs: Override arguments for the copy.

        Returns:
            New DraggableRectangle instance.
        """
        if offset is None:
            offset = [50, 50]

        x0, y0, x1, y1 = self.canvas.coords(self.rect)
        new_x0 = x0 + offset[0]
        new_y0 = y0 + offset[1]
        new_x1 = x1 + offset[0]
        new_y1 = y1 + offset[1]

        return DraggableRectangle(
            self.canvas, new_x0, new_y0, new_x1, new_y1, dpi=self.dpi, **kwargs
        )

    @classmethod
    def compare(cls, rect1: "DraggableRectangle", rect2: "DraggableRectangle") -> Tuple[bool, dict]:
        """
        Compare two rectangles for equality with detailed information.

        Args:
            rect1: First rectangle.
            rect2: Second rectangle.

        Returns:
            Tuple of (are_equal, details_dict).
        """
        pos1 = rect1.get_topleft_pos()
        pos2 = rect2.get_topleft_pos()
        size1 = rect1.get_size()
        size2 = rect2.get_size()

        are_equal = pos1 == pos2 and size1 == size2
        details = {"pos1": pos1, "pos2": pos2, "size1": size1, "size2": size2}
        return are_equal, details

    def get_is_selected(self) -> bool:
        """Get the selection state of this rectangle."""
        return self.is_selected

    def set_is_selected(self, is_selected: bool) -> None:
        """Set the selection state of this rectangle."""
        self.is_selected = is_selected

    def on_click(self, event: "Event") -> None:
        """Handle mouse click on the rectangle body."""
        self.start_x = event.x
        self.start_y = event.y

    def on_drag(self, event: "Event") -> None:
        """
        Handle dragging the rectangle.

        Modifier keys:
            Shift: Lock movement to 45-degree angles (0°, 45°, 90°, 135°, etc.)
        """
        dx: float = event.x - self.start_x
        dy: float = event.y - self.start_y

        if self.keyboard_state.shift_held:
            if dx == 0 and dy == 0:
                return

            angle = math.atan2(dy, dx)
            distance = math.sqrt(dx * dx + dy * dy)

            angle_degrees = math.degrees(angle)
            snap_angle = round(angle_degrees / 45) * 45
            snap_angle_rad = math.radians(snap_angle)

            dx = distance * math.cos(snap_angle_rad)
            dy = distance * math.sin(snap_angle_rad)

        for obj in self.canvas.get_selected():
            obj.canvas.move(obj.rect, dx, dy)
            obj.canvas.move(obj.resize_handle, dx, dy)

        self.start_x = event.x
        self.start_y = event.y

    def on_resize_click(self, event: "Event") -> None:
        """Handle mouse click on the resize handle."""
        self.resize_start_x = event.x
        self.resize_start_y = event.y

    def on_resize_drag(self, event: "Event") -> None:
        """
        Handle dragging the resize handle.

        Modifier keys:
            Shift: Maintain aspect ratio
            Ctrl: Resize from center
            Alt: Constrain to one dimension (horizontal or vertical)
            Shift+Ctrl: Maintain aspect ratio AND resize from center
        """
        dx = event.x - self.resize_start_x
        dy = event.y - self.resize_start_y

        for obj in self.canvas.get_selected():
            x0, y0, x1, y1 = obj.canvas.coords(obj.rect)
            original_width = x1 - x0
            original_height = y1 - y0

            new_dx = dx
            new_dy = dy

            if self.keyboard_state.alt_held:
                if abs(dx) > abs(dy):
                    new_dy = 0
                else:
                    new_dx = 0
            elif self.keyboard_state.shift_held:
                if original_height > 0:
                    aspect_ratio = original_width / original_height

                    if abs(dx) > abs(dy):
                        new_dy = dx / aspect_ratio
                    else:
                        new_dx = dy * aspect_ratio
                else:
                    new_dy = 0

            if self.keyboard_state.ctrl_held:
                new_x0 = x0 - new_dx
                new_y0 = y0 - new_dy
                new_x1 = x1 + new_dx
                new_y1 = y1 + new_dy
            else:
                new_x0 = x0
                new_y0 = y0
                new_x1 = x1 + new_dx
                new_y1 = y1 + new_dy

            if new_x1 > new_x0 and new_y1 > new_y0:
                obj.canvas.coords(obj.rect, new_x0, new_y0, new_x1, new_y1)
                obj.canvas.coords(obj.resize_handle, new_x1, new_y1)

        self.resize_start_x = event.x
        self.resize_start_y = event.y

    def convert_mm_to_px(self, millimeters: float, dpi: Optional[int] = None) -> int:
        """
        Convert millimeters to pixels using DPI.

        Args:
            millimeters: Value in millimeters.
            dpi: DPI for conversion (uses self.dpi if not specified).

        Returns:
            Value in pixels as integer.

        Raises:
            Exception: If conversion fails.
        """
        if dpi is None:
            dpi = self.dpi

        try:
            pixels = int(millimeters * dpi / 25.4)
            return pixels
        except Exception as e:
            logging.error(f"Failed to convert millimeters to pixels: {e}")
            raise

    def convert_px_to_mm(self, pixels: float, dpi: Optional[int] = None) -> float:
        """
        Convert pixels to millimeters using DPI.

        Args:
            pixels: Value in pixels.
            dpi: DPI for conversion (uses self.dpi if not specified).

        Returns:
            Value in millimeters as float.

        Raises:
            Exception: If conversion fails.
        """
        if dpi is None:
            dpi = self.dpi

        try:
            millimeters = pixels * 25.4 / dpi
            return millimeters
        except Exception as e:
            logging.error(f"Failed to convert pixels to millimeters: {e}")
            raise
