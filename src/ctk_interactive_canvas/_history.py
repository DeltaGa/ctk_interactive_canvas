"""saves_history decorator for DraggableRectangle methods.

Provides a parametric decorator that auto-saves a canvas history snapshot
after a method executes.  Works on both instance methods and classmethods
of ``DraggableRectangle`` without requiring an explicit import of that
class (duck-typing via ``hasattr``).
"""

import functools
from collections.abc import Callable
from typing import Any, Optional


def saves_history(
    func: Optional[Callable] = None,
    *,
    only_if_result: bool = False,
) -> Any:
    """Decorator that saves a canvas history snapshot after the method executes.

    Can be applied to both instance methods and classmethods of
    ``DraggableRectangle``.  Uses duck-typing (``hasattr``) so it works
    regardless of class-definition order.

    For classmethods the first argument is the class itself; the second
    argument must be the ``rectangles`` list (the ``align`` / ``distribute``
    convention).  History is saved through ``rectangles[0]._save_history()``.

    Args:
        only_if_result: When *True*, the snapshot is skipped if the decorated
            method returns a falsy value (e.g. ``None`` for a failed
            intersection in ``__and__``).

    Examples::

        # Plain usage (instance method)
        @saves_history
        def __iadd__(self, offset): ...

        # With parameter (classmethod that may return None)
        @saves_history(only_if_result=True)
        def __and__(self, other): ...

        # Classmethod
        @classmethod
        @saves_history
        def align(cls, rectangles, mode, relative_pos=None): ...
    """

    def decorator(f: Callable) -> Callable:
        @functools.wraps(f)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            result = f(*args, **kwargs)
            if only_if_result and not result:
                return result
            first = args[0] if args else None
            if first is None:
                return result
            # Classmethod check first (isinstance(cls, type) is True), then
            # instance method. Must check type before hasattr because the class
            # itself has _save_history as an unbound method.
            if isinstance(first, type):
                # Classmethod call: args[0] is the class, args[1] is rectangles
                rects = args[1] if len(args) > 1 else kwargs.get("rectangles", [])
                if rects and hasattr(rects[0], "_save_history"):
                    rects[0]._save_history()
            elif hasattr(first, "_save_history"):
                # Instance method: args[0] is a DraggableRectangle
                first._save_history()
            return result

        return wrapper

    if func is not None:
        # Bare decorator: @saves_history
        return decorator(func)
    # Parameterised: @saves_history(only_if_result=True)
    return decorator
