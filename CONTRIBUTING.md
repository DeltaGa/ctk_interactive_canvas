# Contributing to CTk Interactive Canvas

Thank you for your interest in contributing to CTk Interactive Canvas! This document provides guidelines and instructions for contributing.

## Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Assume good intentions
- Help others learn and grow

## How to Contribute

### Reporting Bugs

1. **Check existing issues** - Search the issue tracker first
2. **Create a clear report** - Include:
   - Python version
   - CustomTkinter version
   - Operating system
   - Minimal code to reproduce the issue
   - Expected vs actual behavior
   - Error messages and tracebacks

### Suggesting Features

1. **Check existing issues** - Someone may have already suggested it
2. **Describe the use case** - Explain why this feature is needed
3. **Provide examples** - Show how it would be used
4. **Consider alternatives** - Discuss other approaches

### Submitting Pull Requests

#### Before You Start

1. **Discuss major changes** - Open an issue first for significant changes
2. **Check for existing work** - Review open pull requests
3. **Fork the repository** - Work in your own fork

#### Development Setup

```bash
git clone https://github.com/YourUsername/ctk_interactive_canvas.git
cd ctk_interactive_canvas
pip install -e ".[dev]"
```

#### Code Standards

**Style Guidelines**:
- Follow PEP 8
- Use PEP 257 docstrings
- Type hints on all functions/methods
- Line length: 100 characters maximum
- No comments (documentation via docstrings only)

**Run formatters**:
```bash
black .
ruff check --fix .
```

**Type checking**:
```bash
mypy src/ctk_interactive_canvas
```

#### Testing Requirements

1. **Write tests** - All new features must include tests
2. **Maintain coverage** - Aim for >80% code coverage
3. **Run test suite**:
```bash
pytest
```

4. **Run with coverage**:
```bash
pytest --cov=ctk_interactive_canvas --cov-report=term-missing
```

#### Commit Guidelines

**Commit messages**:
- Use present tense ("Add feature" not "Added feature")
- Be descriptive and concise
- Reference issue numbers when applicable

**Example**:
```
Add support for polygon shapes (#123)

- Implement DraggablePolygon class
- Add polygon creation methods to InteractiveCanvas
- Include tests for polygon operations
```

#### Pull Request Process

1. **Update documentation** - Modify README.md if needed
2. **Update CHANGELOG.md** - Add entry under [Unreleased]
3. **Ensure tests pass** - All CI checks must pass
4. **Request review** - Tag maintainers if needed
5. **Address feedback** - Respond to review comments

### Code Organization

```
ctk_interactive_canvas/
├── src/
│   └── ctk_interactive_canvas/
│       ├── __init__.py
│       ├── interactive_canvas.py
│       └── draggable_rectangle.py
├── tests/
│   ├── test_canvas.py
│   ├── test_rectangle.py
│   └── test_integration.py
├── pyproject.toml
└── README.md
```

### Development Philosophy

**Core Principles**:
1. **Simplicity** - Prefer simple, clear solutions
2. **Performance** - Optimize hot paths, profile before optimizing
3. **Compatibility** - Maintain backwards compatibility when possible
4. **Documentation** - Code should be self-documenting
5. **Type Safety** - Use type hints throughout

**What We Value**:
- Clean, readable code over clever tricks
- Comprehensive tests over perfect coverage metrics
- User experience over feature count
- Backwards compatibility over breaking changes

### Adding New Features

**Checklist**:
- [ ] Feature discussed in an issue
- [ ] Code follows style guidelines
- [ ] Type hints added
- [ ] Docstrings added (PEP 257)
- [ ] Tests written (>80% coverage)
- [ ] Tests pass
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] No breaking changes (or documented and justified)

### Performance Guidelines

- Profile before optimizing
- Use appropriate data structures
- Avoid premature optimization
- Document performance-critical sections
- Include benchmarks for significant optimizations

### Documentation Standards

**Docstrings** (PEP 257):
```python
def function(arg1: int, arg2: str) -> bool:
    """
    Brief one-line description.
    
    Args:
        arg1: Description of arg1.
        arg2: Description of arg2.
    
    Returns:
        Description of return value.
    
    Raises:
        ValueError: When this happens.
    """
```

**README updates**:
- Keep examples simple and clear
- Test all code examples
- Update API reference if needed

### Release Process

(Maintainers only)

1. Update version in `pyproject.toml` and `src/ctk_interactive_canvas/__init__.py`
2. Update CHANGELOG.md with release date
3. Create git tag: `git tag -a v0.x.0 -m "Release 0.x.0"`
4. Push tag: `git push origin v0.x.0`
5. GitHub Actions will automatically publish to PyPI

### Questions?

- **Documentation**: Check README.md first
- **Issues**: Search existing issues
- **Discussions**: Use GitHub Discussions for questions
- **Contact**: dev.github.tkjoramsmith@outlook.com

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

**Thank you for contributing!** 🎉
