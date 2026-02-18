# CTk Interactive Canvas

<a href="https://www.codefactor.io/repository/github/deltaga/ctk_interactive_canvas"><img src="https://www.codefactor.io/repository/github/deltaga/ctk_interactive_canvas/badge" alt="CodeFactor" /></a>
<a target="new" href="https://pypi.python.org/pypi/ctk-interactive-canvas"><img border=0 src="https://img.shields.io/badge/python-3.9+-blue.svg?style=flat" alt="Python version"></a>
<a target="new" href="https://pypi.python.org/pypi/ctk-interactive-canvas"><img border=0 src="https://img.shields.io/pypi/v/ctk-interactive-canvas.svg?maxAge=60%" alt="PyPi version"></a>
<a target="new" href="https://pypi.python.org/pypi/ctk-interactive-canvas"><img border=0 src="https://img.shields.io/pypi/status/ctk-interactive-canvas.svg?maxAge=60" alt="PyPi status"></a>
<a target="new" href="https://pypi.python.org/pypi/ctk-interactive-canvas"><img border=0 src="https://img.shields.io/pypi/dm/ctk-interactive-canvas.svg?maxAge=86400&label=installs&color=%2327B1FF" alt="PyPi downloads"></a>
<a target="new" href="https://github.com/DeltaGa/ctk_interactive_canvas"><img border=0 src="https://img.shields.io/github/stars/DeltaGa/ctk_interactive_canvas.svg?style=social&label=Star&maxAge=60" alt="Star this repo"></a>

Interactive canvas widget for CustomTkinter with draggable, resizable rectangles featuring multi-selection, alignment, distribution, and professional-grade interaction controls.

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Real-World Applications](#real-world-applications)
- [Usage Examples](#usage-examples)
- [Keyboard Modifiers](#keyboard-modifiers)
- [API Reference](#api-reference)
- [Requirements](#requirements)
- [Development](#development)
- [License](#license)
- [Credits](#credits)
- [Contributing](#contributing)
- [Changelog](#changelog)
- [Support](#support)

## Features

### Core Capabilities
- **Draggable Rectangles**: Click and drag to move objects
- **Resizable Objects**: Bottom-right handle for intuitive resizing
- **Multi-Selection**: Shift-click or drag-select multiple objects
- **Alignment Tools**: Align multiple rectangles (top, middle, bottom, start, center, end)
- **Distribution Tools**: Evenly distribute rectangles horizontally or vertically
- **Panning**: Middle-mouse or Space+drag to pan the canvas

### Professional Controls
- **Adobe Illustrator-style Constraints**:
  - **Shift during move**: Lock to 45-degree angles (0°, 45°, 90°, 135°, etc.)
  - **Shift during resize**: Maintain aspect ratio
  - **Ctrl during resize**: Resize from center
  - **Alt during resize**: Constrain to one dimension
  - **Shift+Ctrl during resize**: Aspect ratio + center resize

### Advanced Features
- **26 Magic Methods**: NumPy-like interface for geometric operations
- **Unit Conversion**: Built-in mm ↔ px conversion with DPI support
- **Intersection & Union**: Geometric operations via `&` and `|` operators
- **Point Containment**: Test if coordinates are inside rectangles
- **Sorting & Comparison**: Area-based ordering and equality testing
- **Coordinate Access**: Index-based access and iteration

## Installation

```bash
pip install ctk-interactive-canvas
```

## Quick Start

```python
import customtkinter as ctk
from ctk_interactive_canvas import InteractiveCanvas

root = ctk.CTk()
root.title("Interactive Canvas Demo")

canvas = InteractiveCanvas(root, width=800, height=600, bg='white')
canvas.pack()

rect1 = canvas.create_draggable_rectangle(50, 50, 150, 150, outline='blue', width=5)
rect2 = canvas.create_draggable_rectangle(200, 200, 300, 300, outline='red', width=5)

root.mainloop()
```

## Usage Examples

### Basic Rectangle Creation

```python
canvas = InteractiveCanvas(root, width=800, height=600, bg='white')
canvas.pack()

rect = canvas.create_draggable_rectangle(
    x1=100, y1=100,
    x2=200, y2=200,
    outline='blue',
    width=5,
    fill=''
)
```

### Selection Callbacks

```python
def on_select():
    selected = canvas.get_selected()
    print(f"Selected: {len(selected)} objects")

def on_deselect():
    print("Selection cleared")

canvas = InteractiveCanvas(
    root,
    width=800,
    height=600,
    select_callback=on_select,
    deselect_callback=on_deselect
)
```

### Alignment and Distribution

```python
from ctk_interactive_canvas import DraggableRectangle

rectangles = [rect1, rect2, rect3]

DraggableRectangle.align(rectangles, mode='center')
DraggableRectangle.distribute(rectangles, mode='horizontal')
```

### Mathematical Operations

```python
translated = rect + [50, 30]

doubled = rect * 2

halved = rect / 2

rect += [10, 10]

intersection = rect1 & rect2
bounding = rect1 | rect2

if [x, y] in rect:
    print("Point inside rectangle!")

sorted_rects = sorted([rect1, rect2, rect3])
```

### Unit Conversion

```python
rect = canvas.create_draggable_rectangle(0, 0, 100, 100)

pos_mm = rect.get_topleft_pos(in_mm=True, dpi=300)
print(f"Position in mm: {pos_mm}")

rect.set_size([50, 50], in_mm=True, dpi=300)
```

### Coordinate Access

```python
x0, y0, x1, y1 = rect

rect[2] = 300

coords = rect[:]

for coord in rect:
    print(coord)
```

## Keyboard Modifiers

| Action | Modifier | Behavior |
|--------|----------|----------|
| **Move** | Shift | Lock to 45° angles |
| **Resize** | Shift | Maintain aspect ratio |
| **Resize** | Ctrl | Resize from center |
| **Resize** | Alt | Constrain to one axis |
| **Resize** | Shift+Ctrl | Aspect ratio + center |
| **Pan** | Space | Enable pan mode |
| **Select** | Shift+Click | Add to selection |
| **Delete** | Delete | Remove selected |

## API Reference

### InteractiveCanvas

```python
InteractiveCanvas(
    master=None,
    select_callback=None,
    deselect_callback=None,
    delete_callback=None,
    select_outline_color='#16fff6',
    dpi=300,
    create_bindings=True,
    **kwargs
)
```

**Methods**:
- `create_draggable_rectangle(x1, y1, x2, y2, **kwargs)` → DraggableRectangle
- `copy_draggable_rectangle(rect, offset=[21, 21], **kwargs)` → DraggableRectangle
- `delete_draggable_rectangle(item_id)` → None
- `get_selected()` → List[DraggableRectangle]
- `get_draggable_rectangle(item_id)` → DraggableRectangle
- `select_all()` → None
- `deselect_all()` → None

### DraggableRectangle

**Position & Size**:
- `get_topleft_pos(relative_pos=None, in_mm=False, dpi=None)` → [x, y]
- `set_topleft_pos(new_pos, relative_pos=None, in_mm=False, dpi=None)`
- `get_size(in_mm=False, dpi=None)` → [width, height]
- `set_size(new_size, in_mm=False, dpi=None)`

**Transformations**:
- `safe_rotate(angle, anchor='topleft')` - Rotate 90°/180°/-90°/-180°
- `copy_(offset=[50, 50], **kwargs)` → DraggableRectangle

**Class Methods**:
- `align(rectangles, mode, relative_pos=None)` - Align multiple rectangles
- `distribute(rectangles, mode, relative_pos=None)` - Distribute evenly
- `compare(rect1, rect2)` → (bool, dict) - Compare two rectangles
- `get_instances()` → List[DraggableRectangle] - Get all alive instances

**Magic Methods**:
- Arithmetic: `+`, `-`, `*`, `/`, `+=`, `-=`, `*=`, `/=`
- Comparison: `==`, `!=`, `<`, `<=`, `>`, `>=`
- Bitwise: `&` (intersection), `|` (union)
- Unary: `-`, `+`, `abs()`
- Container: `len()`, `[]`, `in`, `iter()`
- Representation: `str()`, `repr()`, `format()`, `bool()`, `hash()`

## Requirements

- Python ≥ 3.9
- CustomTkinter ≥ 5.1.0

## Development

### Install Development Dependencies

```bash
pip install -e ".[dev]"
```

### Run Tests

```bash
pytest
```

### Code Quality

```bash
black .
ruff check .
mypy src/ctk_interactive_canvas
```

## License

MIT License - see [LICENSE](https://github.com/DeltaGa/ctk_interactive_canvas/blob/main/LICENSE) file for details.

## Credits

### Author
**T. K. Joram Smith (DeltaGa)**
- Email: dev.github.tkjoramsmith@outlook.com
- GitHub: [@DeltaGa](https://github.com/DeltaGa)

### Acknowledgments
- [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) - Modern UI framework
- Python Community - Continuous ecosystem evolution

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](https://github.com/DeltaGa/ctk_interactive_canvas/blob/main/CONTRIBUTING.md) for guidelines.

## Changelog

See [CHANGELOG.md](https://github.com/DeltaGa/ctk_interactive_canvas/blob/main/CHANGELOG.md) for version history.

## Support

- **Issues**: [GitHub Issues](https://github.com/DeltaGa/ctk_interactive_canvas/issues)
- **Discussions**: [GitHub Discussions](https://github.com/DeltaGa/ctk_interactive_canvas/discussions)

---

**Note**: This package is in active development. APIs may change between minor versions until 1.0.0 release.
