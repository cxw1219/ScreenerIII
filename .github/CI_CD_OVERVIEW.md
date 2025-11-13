# ScreenerIII CI/CD Pipeline Overview

This document provides an overview of the GitHub Actions CI/CD pipeline configured for the ScreenerIII project.

## Workflow Files

### 1. **ci.yml** - Main CI Pipeline
**Triggers:** Push to main/develop, Pull Requests
**Matrix:** Python 3.9, 3.10, 3.11

**Jobs:**
- **lint-and-test** (matrix strategy):
  - Checkout code
  - Setup Python with pip caching
  - Install dependencies (requirements.txt + requirements-dev.txt)
  - Black code formatting check
  - Flake8 linting (with relaxed error checking)
  - MyPy type checking
  - Bandit security scanning
  - Pytest with coverage reporting
  - Upload coverage to Codecov
  - Archive coverage reports

- **code-quality**:
  - Run pylint for code quality
  - Verify coverage threshold (80% minimum)
  - Must pass for CI to succeed

**Key Features:**
- Matrix testing across 3 Python versions
- Pip dependency caching for faster builds
- Comprehensive code quality checks
- Coverage enforcement (80% threshold)

---

### 2. **test.yml** - Comprehensive Testing
**Triggers:** Push to main/develop, Pull Requests, Daily schedule (2 AM UTC)

**Jobs:**
- **unit-tests** (matrix: Python 3.9, 3.10, 3.11):
  - Run `pytest tests/unit`
  - Upload JUnit XML reports
  - Fast feedback on unit test failures

- **integration-tests**:
  - Uses PostgreSQL service (TimescaleDB)
  - Waits for database readiness
  - Runs `pytest tests/integration`
  - Tests database connectivity
  - Upload JUnit XML reports

- **coverage-report**:
  - Generates coverage reports (XML, HTML, terminal)
  - Enforces 80% coverage threshold
  - Uploads to Codecov
  - Comments on PRs with coverage summary

- **test-summary**:
  - Provides overall test summary
  - Runs after all tests complete

**Key Features:**
- Parallel unit testing across Python versions
- Database integration testing with real TimescaleDB
- Coverage enforcement and reporting
- PR comments with coverage comparison

---

### 3. **security.yml** - Security Scanning
**Triggers:** Push to main/develop, Pull Requests, Weekly schedule (Monday 9 AM UTC)

**Jobs:**
- **bandit-scan**:
  - Scans Python code for security issues
  - Generates JSON and text reports
  - Comments on PRs with findings
  - Uploads bandit report artifact

- **pip-audit**:
  - Audits dependencies for known vulnerabilities
  - Generates JSON report
  - Fails on vulnerabilities (advisory level)
  - Uploads pip-audit report artifact

- **detect-secrets**:
  - Scans for exposed secrets in code
  - Detects API keys, credentials, tokens
  - Uploads secrets report artifact
  - Helps prevent accidental credential commits

- **create-security-issue**:
  - Creates GitHub issue if security issues found (on schedule)
  - Links to detailed workflow artifacts
  - Labeled with 'security' and 'automated' tags

- **security-summary**:
  - Provides summary of all security checks

**Key Features:**
- Multiple security scanning tools
- Weekly automated scanning
- GitHub issue creation for findings
- Artifact collection for review

---

### 4. **docker.yml** - Docker Build and Test
**Triggers:** Push to main/develop, Tags (v*.*.*), Pull Requests

**Jobs:**
- **build**:
  - Sets up Docker Buildx
  - Logs into container registry (GHCR)
  - Builds Docker image with metadata
  - Caches layers for faster builds
  - Pushes on main branch (not PRs)

- **test** (PR only):
  - Loads Docker image for testing
  - Validates docker-compose.yml
  - Tests PostgreSQL service connectivity
  - Runs basic container tests
  - Tests database connection from container
  - Cleanup after tests

- **docker-compose**:
  - Validates docker-compose.yml syntax
  - Tests docker-compose up behavior
  - Checks service startup
  - Logs collection for debugging

- **push-to-registry** (main branch only):
  - Builds and pushes final image to GHCR
  - Tags with branch, version, and latest
  - Only runs after all tests pass

**Key Features:**
- Multi-platform Docker builds
- GitHub Container Registry integration
- Comprehensive Docker testing
- Automatic tagging strategy
- Build layer caching

**Registry:** ghcr.io (GitHub Container Registry)
**Tags:** branch, semver versions, latest

---

### 5. **docs.yml** - Documentation Checks
**Triggers:** Push to main/develop (docs changes), Pull Requests (docs changes)

**Jobs:**
- **markdown-lint**:
  - Lints all markdown files
  - Validates markdown syntax
  - Non-blocking warnings

- **link-check**:
  - Checks markdown links for validity
  - HTTP/HTTPS link validation
  - 10-second timeout per link
  - Reports broken links

- **docstring-check**:
  - Validates Python docstrings
  - Uses pydocstyle
  - Checks PEP 257 compliance
  - Non-blocking

- **readme-completeness**:
  - Verifies README.md exists
  - Checks for required sections:
    - Installation
    - Usage
    - Configuration
    - Contributing
  - Warns if sections missing

- **docs-build** (if docs/ exists):
  - Attempts Sphinx documentation build
  - Builds HTML documentation
  - Uploads documentation artifact
  - Non-blocking if Sphinx not configured

- **docs-summary**:
  - Overall documentation check summary

**Key Features:**
- Comprehensive documentation validation
- Markdown and link checking
- Python docstring validation
- Optional Sphinx support
- Build artifact preservation

---

## Configuration Files

### 1. **dependabot.yml** - Automated Dependency Updates
Configures Dependabot for automated dependency management:

- **pip**: Weekly updates (Mondays 10 AM UTC)
  - Limits to 5 open PRs
  - Labels: dependencies, python
  - Prefix commits with `chore(deps):`

- **github-actions**: Weekly updates (Tuesdays 10 AM UTC)
  - Limits to 3 open PRs
  - Labels: ci/cd, github-actions
  - Prefix commits with `ci(actions):`

- **docker**: Weekly updates (Wednesdays 10 AM UTC)
  - Labels: dependencies, docker
  - Prefix commits with `chore(docker):`

**Features:**
- Automated security updates
- Grouped PR management
- Convenient commit prefixes
- Scheduled dependency checks

---

### 2. **CODEOWNERS** - Automatic PR Reviewers
Specifies code owners for automatic PR review assignment:

- **Default**: @owner (all files)
- **.github/workflows/**: @owner
- **config/**: @owner
- **src/**: @owner
- **tests/**: @owner
- **docs/**: @owner
- And more specific paths...

**Features:**
- Automatic reviewer assignment
- Path-based reviewer routing
- PR approval enforcement possible

---

### 3. **PULL_REQUEST_TEMPLATE.md** - PR Guidelines
Standardized PR template with sections for:

- **Description**: Brief change overview
- **Type of Change**: Bug fix, feature, breaking change, etc.
- **Related Issues**: Link to GitHub issues
- **Changes Made**: Detailed list of changes
- **Testing**: Testing coverage and results
- **Code Quality**: Verification checklist
- **Documentation**: Documentation updates
- **Performance Impact**: Performance considerations
- **Backward Compatibility**: Compatibility notes
- **Database Changes**: Schema migration info
- **Deployment Notes**: Special deployment info
- **Screenshots**: UI change screenshots
- **Checklist**: Final verification items

**Features:**
- Comprehensive PR structure
- Code quality reminders
- Test coverage documentation
- Backward compatibility tracking
- Deployment awareness

---

## Workflow Summary

| Workflow | Trigger | Schedule | Purpose |
|----------|---------|----------|---------|
| ci.yml | Push/PR | On demand | Code quality & testing |
| test.yml | Push/PR | Daily 2 AM UTC | Comprehensive testing |
| security.yml | Push/PR | Weekly Mon 9 AM UTC | Security scanning |
| docker.yml | Push/PR/Tags | On demand | Docker build & test |
| docs.yml | Push/PR (docs) | On demand | Documentation validation |

---

## Environment Variables & Secrets

### Required GitHub Secrets:
- `GITHUB_TOKEN`: (automatically available)

### Optional Secrets:
- `CODECOV_TOKEN`: For Codecov coverage reporting
- Docker registry credentials (if using Docker Hub)

---

## Code Quality Standards

### Coverage Requirements
- Minimum: 80%
- Fail on lower coverage

### Code Formatting
- **Black**: Automatic code formatting
- **Flake8**: PEP 8 linting
- **MyPy**: Python type checking
- **Bandit**: Python security

### Testing
- Unit tests: All Python versions (3.9, 3.10, 3.11)
- Integration tests: Real database (TimescaleDB)
- Coverage report: Generated and published

### Security
- Dependency vulnerability scanning (pip-audit)
- Python code security (bandit)
- Secret detection (detect-secrets)

---

## Local Development Setup

To match the CI pipeline locally:

```bash
# Install dev dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run formatting
black src/ tests/ main.py setup.py

# Run linting
flake8 src/ tests/ main.py setup.py

# Run type checking
mypy src/ tests/ main.py

# Run security scan
bandit -r src/ main.py

# Run tests with coverage
pytest tests/ --cov=src --cov-report=html

# Run with docker-compose
docker-compose up -d
```

---

## PR Workflow

1. Create PR against main/develop
2. Workflows automatically trigger:
   - Code quality checks (ci.yml)
   - Test suite runs (test.yml)
   - Docker build tests (docker.yml)
   - Documentation validation (docs.yml)
3. Fix any failures indicated by workflow status
4. Once all checks pass, request review
5. Reviewers assigned via CODEOWNERS
6. After merge, security scans run weekly

---

## Troubleshooting

### Coverage failures
- Ensure all new code has tests
- Run locally: `pytest tests/ --cov=src --cov-report=term-missing`

### Type checking failures
- Add type hints to function signatures
- Use `typing` module for complex types

### Bandit security warnings
- Review each warning for legitimacy
- Use `# nosec` comment if safe (with caution)

### Docker build failures
- Check Dockerfile for syntax errors
- Ensure all dependencies installed in Dockerfile
- Test locally: `docker build -t screeneriii:test .`

### Link check failures
- Verify URLs are valid and accessible
- Check for typos in links
- Some links may need timeout adjustments

---

## Customization

### Adding/Modifying Workflows
1. Edit files in `.github/workflows/`
2. Test locally with act (GitHub Actions local runner)
3. Commit and push to trigger workflow

### Updating Coverage Threshold
- Edit `ci.yml` or `test.yml`
- Change `coverage < 80` to desired percentage

### Adding New Python Version
- Update matrix in `ci.yml` and `test.yml`
- Add to version list in `.github/workflows/*.yml`

### Modifying Dependabot
- Edit `.github/dependabot.yml`
- Change schedule intervals, limits, or labels

---

## Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Black Code Formatter](https://github.com/psf/black)
- [Flake8 Linter](https://flake8.pycqa.org/)
- [MyPy Type Checker](https://www.mypy-lang.org/)
- [Bandit Security Scanner](https://bandit.readthedocs.io/)
- [Pytest Testing Framework](https://pytest.org/)
- [Codecov Coverage Reporting](https://codecov.io/)
