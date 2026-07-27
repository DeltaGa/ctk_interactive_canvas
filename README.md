[![CodeFactor](https://www.codefactor.io/repository/github/deltaga/ctk_interactive_canvas/badge)](https://www.codefactor.io/repository/github/deltaga/ctk_interactive_canvas)
[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![PyPI](https://img.shields.io/pypi/v/ctk-interactive-canvas.svg)](https://pypi.python.org/pypi/ctk-interactive-canvas)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

# CTk Interactive Canvas v0.9.0

## Draggable, Resizable Rectangles for CustomTkinter

**Version:** 0.9.0  
**Release Date:** March 16, 2026  
**Python:** 3.9+  
**CustomTkinter:** 5.1.0+

---

## Table of Contents

- [Overview](#overview)
- [System Requirements](#system-requirements)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage Examples](#usage-examples)
- [Keyboard Modifiers](#keyboard-modifiers)
- [API Reference](#api-reference)
- [Development](#development)
- [Status](#status)
- [Contributing](#contributing)
- [Changelog](#changelog)
- [Credits](#credits)
- [License](#license)

---

## Overview

An interactive canvas widget for CustomTkinter. It provides draggable, resizable rectangles with multi-selection, alignment, distribution, panning, and zoom. Rectangles behave as geometric objects with a NumPy-like operator interface, so translation, scaling, intersection, and union are expressed directly in code.

### Key Capabilities

- **Direct manipulation** - Drag to move, resize from the bottom-right handle, multi-select by shift-click or drag-select
- **Layout tools** - Align and distribute selected rectangles across six alignment modes and both axes
- **Editor-style constraints** - Modifier keys lock angles, aspect ratio, center-anchoring, and single-axis resize
- **Operator interface** - Arithmetic, comparison, bitwise intersection and union, and container access on rectangles
- **Unit conversion** - Built-in millimeter and pixel conversion with DPI support
- **History and zoom** - Undo/redo and viewport-anchored zoom, both configurable at construction

---

## System Requirements

- **Python:** 3.9 or later
- **CustomTkinter:** 5.1.0 or later

---

## Installation

```bash
pip install ctk-interactive-canvas
```

---

## Quick Start

```python
import customtkinter as ctk
from ctk_interactive_canvas import InteractiveCanvas

root = ctk.CTk()
root.title("Interactive Canvas Demo")

canvas = InteractiveCanvas(root, width=800, height=600, bg="white")
canvas.pack()

canvas.create_draggable_rectangle(50, 50, 150, 150, outline="blue", width=5)
canvas.create_draggable_rectangle(200, 200, 300, 300, outline="red", width=5)

root.mainloop()
```

---

## Usage Examples

### Selection Callbacks

```python
def on_select():
    print(f"Selected: {len(canvas.get_selected())} objects")

def on_deselect():
    print("Selection cleared")

canvas = InteractiveCanvas(
    root, width=800, height=600,
    select_callback=on_select,
    deselect_callback=on_deselect,
)
```

### Alignment and Distribution

```python
from ctk_interactive_canvas import DraggableRectangle

DraggableRectangle.align([rect1, rect2, rect3], mode="center")
DraggableRectangle.distribute([rect1, rect2, rect3], mode="horizontal")
```

### Operator Interface

```python
translated = rect + [50, 30]      # translate
doubled = rect * 2                # scale
intersection = rect1 & rect2      # geometric intersection
bounding = rect1 | rect2          # bounding union

if [x, y] in rect:                # point containment
    ...

sorted_rects = sorted([rect1, rect2, rect3])   # area-based ordering
```

### Unit Conversion

```python
pos_mm = rect.get_topleft_pos(in_mm=True, dpi=300)
rect.set_size([50, 50], in_mm=True, dpi=300)
```

---

## Keyboard Modifiers

| Action | Modifier | Behavior |
|--------|----------|----------|
| Move | Shift | Lock to 45-degree angles |
| Resize | Shift | Maintain aspect ratio |
| Resize | Ctrl | Resize from center |
| Resize | Alt | Constrain to one axis |
| Resize | Shift+Ctrl | Aspect ratio and center |
| Pan | Space | Enable pan mode |
| Select | Shift+Click | Add to selection |
| Delete | Delete | Remove selected |

---

## API Reference

### InteractiveCanvas

```python
InteractiveCanvas(
    master=None,
    select_callback=None,
    deselect_callback=None,
    delete_callback=None,
    select_outline_color="#16fff6",
    dpi=300,
    create_bindings=True,
    **kwargs,
)
```

| Method | Returns |
|--------|---------|
| `create_draggable_rectangle(x1, y1, x2, y2, **kwargs)` | `DraggableRectangle` |
| `copy_draggable_rectangle(rect, offset=[21, 21], **kwargs)` | `DraggableRectangle` |
| `delete_draggable_rectangle(item_id)` | `DraggableRectangle | None` |
| `get_draggable_rectangle(item_id)` | `DraggableRectangle` |
| `get_selected()` | `List[DraggableRectangle]` |
| `select_all()` / `deselect_all()` | `None` |

### DraggableRectangle

**Position and size**

- `get_topleft_pos(relative_pos=None, in_mm=False, dpi=None)`
- `set_topleft_pos(new_pos, relative_pos=None, in_mm=False, dpi=None)`
- `get_size(in_mm=False, dpi=None)`
- `set_size(new_size, in_mm=False, dpi=None)`

**Transformations**

- `safe_rotate(angle, anchor="topleft")`
- `copy_(offset=[50, 50], **kwargs)`

**Class methods**

- `align(rectangles, mode, relative_pos=None)`
- `distribute(rectangles, mode, relative_pos=None)`
- `compare(rect1, rect2)`
- `get_instances()`

**Operators**

- Arithmetic: `+`, `-`, `*`, `/` and augmented forms
- Comparison: `==`, `!=`, `<`, `<=`, `>`, `>=`
- Bitwise: `&` (intersection), `|` (union)
- Container: `len()`, `[]`, `in`, iteration

---

## Development

```bash
# Install with development dependencies
pip install -e ".[dev]"

# Run the test suite
pytest

# Format, lint, and type-check
black .
ruff check .
mypy src/ctk_interactive_canvas
```

---

## Status

This package is in active development (Beta). The public API may change between minor versions until the 1.0.0 release. See the [Changelog](CHANGELOG.md) for version history.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Code follows the conventions in [STYLE.md](STYLE.md) and [OPTIMIZATION.md](OPTIMIZATION.md).

---

## Changelog

Full version history is in [CHANGELOG.md](CHANGELOG.md).

---

## Credits

### Author

**Tchicdje Kouojip Joram Smith (DeltaGa)**  
Email: dev.github.tkjoramsmith@outlook.com  
GitHub: [https://github.com/DeltaGa](https://github.com/DeltaGa)

### Acknowledgments

- [**CustomTkinter**](https://github.com/TomSchimansky/CustomTkinter): The widget foundation this package builds on.

---

## License

Released under the MIT License. See [LICENSE](LICENSE) for details.

---

© 2026 DeltaGa. All rights reserved.
