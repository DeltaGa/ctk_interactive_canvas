# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.3] - 2026-02-15

Major feature release with history, zoom, and improved user experience.

### Added
- **History System**: Optional undo/redo functionality (enabled by default)
  - `enable_history` parameter in InteractiveCanvas
  - Keyboard shortcuts: Ctrl+Z (undo), Ctrl+Y or Ctrl+Shift+Z (redo)
  - Configurable history depth (default: 50 states)
- **Zoom Functionality**: Optional zoom in/out (enabled by default)
  - `enable_zoom` parameter in InteractiveCanvas
  - Keyboard shortcuts: + (zoom in), - (zoom out)
  - Alt+MouseWheel support
  - Configurable zoom range (0.1x to 10x)
- **Centered Rectangle Creation**: `center_on_canvas` parameter in `create_draggable_rectangle()`
  - When True, creates rectangle at visible canvas center (default: False)
  - Maintains specified dimensions while centering position
  - Improves UX in real-world examples
- **Fluid Text Attachment**: Text labels now move with rectangles
  - `attach_text_to_rectangle()` method for linking text to rectangles
  - `move_attached_items()` automatically called during drag operations
  - Prevents text labels from staying fixed when rectangles move
- **Bidirectional Persistence**: Load/import functionality in all real-world examples
  - Document Layout Designer: Load layout from JSON
  - Bounding Box Editor: Load project with annotations
  - Seating Chart Planner: Load seating arrangements
  - Matching save/load workflows for all examples

### Changed
- Real-world examples now use `center_on_canvas=True` for better initial placement
- All example text labels properly attached to parent rectangles
- History automatically saved after rectangle creation

### Fixed
- Text labels remaining stationary when rectangles are dragged
- Initial rectangle placement requiring manual positioning in examples

## [0.3.2] - 2026-02-15

Critical bug fix for magic methods and auto-registration system.

### Added
- **Auto-registration system**: `InteractiveCanvas._register_rectangle()` method for automatic tracking of all DraggableRectangle instances
- Automatic rectangle registration in `DraggableRectangle.__init__()` - ensures rectangles created via any method (magic methods, direct instantiation, or canvas methods) are properly tracked
- Three production-ready real-world examples:
  - `document_layout_designer.py` - Professional page layout tool with PDF export
  - `bounding_box_editor.py` - ML annotation tool with YOLO/COCO export  
  - `seating_chart_planner.py` - Event planning tool with table management

### Fixed
- **CRITICAL**: Automatic rectangle registration in InteractiveCanvas - rectangles created via magic methods (+, *, &, |, etc.) or direct DraggableRectangle instantiation now automatically register with canvas.objects, enabling proper interaction and selection

## [0.3.1] - 2026-02-14

Maintenance and compatibility release improving code quality, testing infrastructure, and example demonstrations.

### Added
- Explicit `width` parameter to `DraggableRectangle.__init__()` for better control over rectangle border thickness
- Randomized coordinate generation in alignment_demo.py for dynamic visual demonstrations
- Visual rectangle overlays for intersection (&) and union (|) operations in magic_methods_demo.py
- Comprehensive pytest fixtures with function-level scope and proper cleanup
- InteractiveCanvas.coords() override for handling anti-aliased circle font elements

### Changed
- Increased default rectangle border width from 2px to 5px across all examples for improved visibility
- Refactored magic_methods_demo.py create_copy() to use canvas.copy_draggable_rectangle() method
- Dropped Python 3.8 support; now requires Python 3.9+
- Enhanced keyboard state management with proper type hints
- Improved coordinate validation with explicit error raising for None checks
- Instance tracking optimized using list comprehension in get_instances()

### Fixed
- Coordinate tuple unpacking with proper type casting to float
- Selection state tracking in on_click() with null checks
- Intersection and union visualization with temporary rectangle cleanup
- Edge cases in aspect ratio maintenance during resize operations
- Zero-height rectangle handling during resize operations
- Weakref memory leak in instance tracking
- GitHub Actions workflow (removed ruff check from CI)
- Tkinter event type hints throughout codebase
- Mutable default arguments in multiple method signatures

### Technical Improvements
- PEP 257 docstring compliance across all public methods
- Full type hint coverage for event handlers and internal methods
- Black code formatting applied throughout codebase
- Virtual display support for testing environments
- Proper fixture scope isolation for pytest reliability

## [0.3.0] - 2024-02-14

### Added
- Adobe Illustrator-style constraint algorithms for movement and resizing
- Ctrl key support for center-anchored resize operations
- 45-degree angle snapping during drag with Shift key
- Comprehensive docstrings on all methods (PEP 257 compliance)
- Combined modifier key support (Shift+Ctrl for aspect ratio + center resize)

### Changed
- Improved movement constraint algorithm from simple axis-locking to professional 45-degree angle snapping
- Enhanced resize constraint logic with proper aspect ratio calculation
- Refactored keyboard state management for better modifier key handling

### Fixed
- Edge cases in aspect ratio maintenance during resize
- Improved zero-height rectangle handling during resize operations

## [0.2.0] - 2024-02-14

### Added
- 26 magic methods for NumPy-like interface
- Mathematical operations: arithmetic (+, -, *, /), augmented assignment (+=, -=, *=, /=)
- Comparison operations: equality (==, !=), ordering (<, <=, >, >=)
- Bitwise operations: intersection (&), union (|)
- Unary operations: negation (-), identity (+), absolute (abs())
- Container protocol: length (len()), indexing ([]), containment (in), iteration
- Representation methods: str(), repr(), format(), bool(), hash()
- Point-in-rectangle containment testing
- Area-based comparison and sorting
- Coordinate access via indexing and slicing
- KeyboardStateManager for per-canvas modifier state isolation

### Changed
- Transformed DraggableRectangle into a full mathematical entity
- Version bumped to 0.2.0 for feature addition

### Fixed
- Weakref memory leak in instance tracking
- Class-level state sharing across multiple canvases
- Mutable default arguments replaced with None checks

## [0.1.0] - 2024-02-14

### Added
- Initial release
- InteractiveCanvas widget with multi-selection support
- DraggableRectangle with resize handles
- Shift-click and drag-select functionality
- Middle-mouse and Space+drag panning
- Alignment tools (top, middle, bottom, start, center, end)
- Distribution tools (horizontal, vertical)
- Unit conversion (millimeters ↔ pixels with DPI support)
- Delete key support for removing selected objects
- Selection callbacks (select, deselect, delete)
- Project-specific path dependencies removed
- Proper package structure with relative imports
- Phase 1 critical bug fixes completed

[Unreleased]: https://github.com/DeltaGa/ctk_interactive_canvas/compare/v0.3.1...HEAD
[0.3.1]: https://github.com/DeltaGa/ctk_interactive_canvas/compare/v0.3.0...v0.3.1
[0.3.2]: https://github.com/DeltaGa/ctk_interactive_canvas/compare/v0.3.1...v0.3.2
[0.3.3]: https://github.com/DeltaGa/ctk_interactive_canvas/compare/v0.3.2...v0.3.3