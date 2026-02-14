# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/DeltaGa/ctk_interactive_canvas/compare/v0.3.0...HEAD