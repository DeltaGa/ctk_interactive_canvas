# Contributing to CTk Interactive Canvas

Contributions are welcome. The guidelines below keep changes reviewable and consistent with the rest of the codebase.

## Reporting Issues

When reporting a bug, include the Python version, CustomTkinter version, operating system, a minimal reproduction, the expected and actual behavior, and any traceback. Search existing issues first.

## Development Setup

```bash
git clone https://github.com/DeltaGa/ctk_interactive_canvas.git
cd ctk_interactive_canvas
pip install -e ".[dev]"
```

## Standards

- Follow the conventions in [STYLE.md](STYLE.md) and [OPTIMIZATION.md](OPTIMIZATION.md).
- PEP 8, PEP 257 docstrings, full type hints, 100-character lines.
- Format and lint before committing:

```bash
black .
ruff check --fix .
mypy src/ctk_interactive_canvas
```

## Testing

All new behavior must include tests. Run the suite with coverage before opening a pull request:

```bash
pytest --cov=ctk_interactive_canvas --cov-report=term-missing
```

## Pull Requests

1. Discuss significant changes in an issue first.
2. Keep commits focused, with present-tense messages that reference issues where applicable.
3. Update the README and add a `CHANGELOG.md` entry under `[Unreleased]`.
4. Ensure the full suite and CI checks pass.

By contributing, you agree that your contributions are licensed under the MIT License.

---

© 2026 DeltaGa. All rights reserved.
