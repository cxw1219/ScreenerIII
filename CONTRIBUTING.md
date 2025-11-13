# Contributing to ScreenerIII

Thank you for your interest in contributing to ScreenerIII! This document provides guidelines and instructions for contributing to the project.

## Code of Conduct

Please be respectful and constructive in all interactions with the project and its community.

## Development Setup

### Prerequisites

- Python 3.8 or higher
- pip package manager
- Git

### Setting Up Your Development Environment

1. Fork and clone the repository:
   ```bash
   git clone https://github.com/yourusername/ScreenerIII.git
   cd ScreenerIII
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up your environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your OANDA API credentials
   ```

5. Install development dependencies (if applicable):
   ```bash
   pip install black pytest pytest-cov flake8
   ```

## Code Style Guidelines

### Python Code Formatting

This project uses **Black** for code formatting with the following configuration:

- Line length: 88 characters (Black's default)
- Use double quotes for strings
- Run Black before committing:
  ```bash
  black .
  ```

### Code Quality

- Follow PEP 8 guidelines
- Use type hints where appropriate
- Write clear, descriptive variable and function names
- Keep functions focused and single-purpose
- Add docstrings to all public functions and classes

### Example Docstring Format

```python
def calculate_indicator(data: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    Calculate a technical indicator for the given data.

    Args:
        data: DataFrame containing OHLCV data
        period: Lookback period for the calculation (default: 14)

    Returns:
        Series containing the calculated indicator values

    Raises:
        ValueError: If data is empty or period is invalid
    """
    pass
```

## Testing Requirements

### Writing Tests

- Write unit tests for all new functionality
- Place tests in the `tests/` directory
- Use pytest for testing
- Aim for at least 80% code coverage

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_specific.py
```

## Commit Message Conventions

Follow these conventions for clear and consistent commit messages:

### Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- **feat**: New feature
- **fix**: Bug fix
- **docs**: Documentation changes
- **style**: Code style changes (formatting, missing semicolons, etc.)
- **refactor**: Code refactoring without changing functionality
- **test**: Adding or updating tests
- **chore**: Maintenance tasks, dependency updates

### Examples

```
feat(screener): add RSI indicator calculation

Implement RSI calculation with configurable period.
Includes proper handling of edge cases.

Closes #123
```

```
fix(api): handle OANDA rate limit errors

Add exponential backoff retry logic for rate-limited requests.
```

```
docs(readme): update installation instructions
```

## Pull Request Process

1. **Create a feature branch:**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes:**
   - Write clean, well-documented code
   - Follow the code style guidelines
   - Add tests for new functionality

3. **Format and test your code:**
   ```bash
   black .
   pytest
   ```

4. **Commit your changes:**
   - Follow the commit message conventions
   - Make atomic commits (one logical change per commit)

5. **Push to your fork:**
   ```bash
   git push origin feature/your-feature-name
   ```

6. **Submit a pull request:**
   - Provide a clear description of the changes
   - Reference any related issues
   - Ensure all tests pass
   - Wait for code review

### Pull Request Checklist

- [ ] Code follows the style guidelines
- [ ] Code has been formatted with Black
- [ ] All tests pass
- [ ] New tests added for new functionality
- [ ] Documentation updated (if applicable)
- [ ] Commit messages follow conventions
- [ ] No merge conflicts with main branch

## Reporting Issues

When reporting issues, please include:

- Clear description of the problem
- Steps to reproduce
- Expected behavior
- Actual behavior
- Python version and OS
- Relevant error messages or logs

## Questions?

If you have questions about contributing, please open an issue with the "question" label.

## License

By contributing to ScreenerIII, you agree that your contributions will be licensed under the MIT License.
