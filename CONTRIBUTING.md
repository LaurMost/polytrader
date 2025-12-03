# Contributing to Polytrader

Thank you for your interest in contributing to Polytrader! This document provides guidelines and information for contributors.

## Code of Conduct

Please be respectful and constructive in all interactions. We're all here to build something useful together.

## Getting Started

### Development Setup

1. **Fork and clone the repository**

   ```bash
   git clone https://github.com/YOUR_USERNAME/polytrader.git
   cd polytrader
   ```

2. **Install uv** (if not already installed)

   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

3. **Install dependencies with dev extras**

   ```bash
   uv sync --all-extras
   ```

4. **Verify setup**

   ```bash
   uv run polytrader --help
   uv run pytest
   ```

### Project Structure

```
polytrader/
├── polytrader/           # Main package
│   ├── analytics/        # Performance metrics
│   ├── core/             # Client, executor, WebSocket
│   ├── data/             # Models, storage
│   ├── indicators/       # Technical indicators
│   ├── strategy/         # Strategy framework
│   └── utils/            # Helpers
├── strategies/           # Example strategies
├── tests/                # Test suite
└── dashboard.py          # Streamlit app
```

## How to Contribute

### Reporting Bugs

1. Check existing issues to avoid duplicates
2. Use the bug report template
3. Include:
   - Python version (`python --version`)
   - Polytrader version (`polytrader --version`)
   - Operating system
   - Steps to reproduce
   - Expected vs actual behavior
   - Error messages/stack traces

### Suggesting Features

1. Check existing issues/discussions
2. Describe the use case
3. Explain why it would be valuable
4. Consider implementation complexity

### Submitting Code

1. **Create a branch**

   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/your-bug-fix
   ```

2. **Make your changes**
   - Follow the code style (see below)
   - Add tests for new functionality
   - Update documentation as needed

3. **Run checks**

   ```bash
   # Lint
   uv run ruff check .
   
   # Format
   uv run ruff format .
   
   # Type check (optional)
   uv run mypy polytrader
   
   # Tests
   uv run pytest
   ```

4. **Commit with clear messages**

   ```bash
   git commit -m "feat: add new indicator for RSI divergence"
   git commit -m "fix: handle empty price history response"
   git commit -m "docs: update README with new CLI commands"
   ```

5. **Push and create a Pull Request**

   ```bash
   git push origin feature/your-feature-name
   ```

## Code Style

### Python Style

- Use [ruff](https://github.com/astral-sh/ruff) for linting and formatting
- Line length: 100 characters
- Use type hints where practical
- Write docstrings for public functions/classes

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation only
- `style:` Code style (formatting, no logic change)
- `refactor:` Code refactoring
- `test:` Adding/updating tests
- `chore:` Maintenance tasks

### Documentation

- Update README.md for user-facing changes
- Add docstrings for new functions/classes
- Include examples in docstrings where helpful

## Testing

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=polytrader

# Run specific test file
uv run pytest tests/test_analytics.py

# Run specific test
uv run pytest tests/test_analytics.py::test_sharpe_ratio
```

### Writing Tests

- Place tests in the `tests/` directory
- Mirror the package structure
- Use descriptive test names
- Test edge cases and error conditions

Example:

```python
# tests/test_analytics.py
import pytest
from polytrader.analytics.metrics import calculate_sharpe

def test_sharpe_ratio_positive_returns():
    returns = [0.01, 0.02, 0.015, 0.01, 0.025]
    sharpe = calculate_sharpe(returns)
    assert sharpe > 0

def test_sharpe_ratio_empty_returns():
    sharpe = calculate_sharpe([])
    assert sharpe == 0.0
```

## Pull Request Process

1. Ensure all checks pass (lint, tests)
2. Update documentation if needed
3. Add entry to CHANGELOG.md under "Unreleased"
4. Request review from maintainers
5. Address review feedback
6. Squash commits if requested

## Areas for Contribution

### Good First Issues

- Adding new technical indicators
- Improving error messages
- Adding tests for existing code
- Documentation improvements

### Larger Projects

- New strategy examples
- Backtesting framework
- Additional data sources
- Performance optimizations

## Questions?

- Open a GitHub Discussion for general questions
- Open an Issue for bugs/features
- Check existing issues/discussions first

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to Polytrader!
