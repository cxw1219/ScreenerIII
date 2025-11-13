#!/bin/bash

# ScreenerIII Development Environment Setup Script
# This script installs and configures pre-commit hooks for development

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

# Main execution
main() {
    print_header "ScreenerIII Development Environment Setup"

    # Get script directory
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

    print_info "Project root: $PROJECT_ROOT"

    # Check if we're in the right directory
    if [ ! -f "$PROJECT_ROOT/.pre-commit-config.yaml" ]; then
        print_error "Not in ScreenerIII project root. Please run this script from the project directory."
        exit 1
    fi

    # Step 1: Check Python version
    print_header "Step 1: Verifying Python Installation"
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed. Please install Python 3.9 or higher."
        exit 1
    fi

    PYTHON_VERSION=$(python3 --version | awk '{print $2}')
    print_success "Python $PYTHON_VERSION found"

    # Step 2: Create virtual environment if it doesn't exist
    print_header "Step 2: Setting Up Virtual Environment"
    if [ ! -d "$PROJECT_ROOT/.venv" ]; then
        print_info "Creating virtual environment..."
        python3 -m venv "$PROJECT_ROOT/.venv"
        print_success "Virtual environment created"
    else
        print_info "Virtual environment already exists"
    fi

    # Activate virtual environment
    source "$PROJECT_ROOT/.venv/bin/activate"
    print_success "Virtual environment activated"

    # Step 3: Upgrade pip, setuptools, and wheel
    print_header "Step 3: Upgrading pip and Build Tools"
    print_info "Upgrading pip, setuptools, and wheel..."
    pip install --upgrade pip setuptools wheel > /dev/null 2>&1
    print_success "pip and build tools upgraded"

    # Step 4: Install pre-commit
    print_header "Step 4: Installing pre-commit"
    if ! command -v pre-commit &> /dev/null; then
        print_info "Installing pre-commit..."
        pip install pre-commit > /dev/null 2>&1
        print_success "pre-commit installed"
    else
        print_info "pre-commit already installed, upgrading..."
        pip install --upgrade pre-commit > /dev/null 2>&1
        print_success "pre-commit upgraded"
    fi

    # Verify pre-commit installation
    PRE_COMMIT_VERSION=$(pre-commit --version)
    print_success "pre-commit version: $PRE_COMMIT_VERSION"

    # Step 5: Install development dependencies
    print_header "Step 5: Installing Development Dependencies"
    print_info "Installing development tools..."

    DEV_PACKAGES=(
        "black>=24.1.1"
        "isort>=5.13.2"
        "flake8>=7.0.0"
        "flake8-bugbear"
        "flake8-comprehensions"
        "flake8-docstrings"
        "pylint>=3.0.3"
        "bandit>=1.7.5"
        "detect-secrets>=1.4.0"
        "mypy>=1.8.0"
        "types-requests"
        "types-PyYAML"
    )

    for package in "${DEV_PACKAGES[@]}"; do
        pip install "$package" > /dev/null 2>&1
    done
    print_success "Development dependencies installed"

    # Step 6: Install pre-commit hooks
    print_header "Step 6: Installing Pre-commit Hooks"
    cd "$PROJECT_ROOT"
    print_info "Installing hooks from .pre-commit-config.yaml..."

    if pre-commit install; then
        print_success "Pre-commit hooks installed successfully"
    else
        print_error "Failed to install pre-commit hooks"
        exit 1
    fi

    # Step 7: Generate secrets baseline (if not exists)
    print_header "Step 7: Setting Up Detect-Secrets"
    if [ ! -f "$PROJECT_ROOT/.secrets.baseline" ]; then
        print_info "Generating detect-secrets baseline..."
        detect-secrets scan --baseline .secrets.baseline > /dev/null 2>&1
        print_success "Secrets baseline generated"
    else
        print_info "Secrets baseline already exists"
    fi

    # Step 8: Run initial pre-commit check
    print_header "Step 8: Running Initial Pre-commit Check"
    print_info "Running pre-commit on all files (this may take a moment)..."

    if pre-commit run --all-files; then
        print_success "Pre-commit checks passed!"
    else
        print_warning "Some pre-commit checks failed (this is expected for first run)"
        print_info "Review the errors above and fix them as needed"
        print_info "Run 'pre-commit run --all-files' to check again"
    fi

    # Step 9: Display setup summary
    print_header "Setup Complete!"
    echo ""
    echo "ScreenerIII development environment is ready!"
    echo ""
    echo "Available commands:"
    echo "  - Run all pre-commit hooks:    pre-commit run --all-files"
    echo "  - Run specific hook:           pre-commit run <hook-id> --all-files"
    echo "  - Check staged files:          pre-commit run"
    echo "  - List all hooks:              pre-commit run --list-files"
    echo ""
    echo "Installed hooks:"
    echo "  Code Formatting:"
    echo "    - black                     (Python code formatter)"
    echo "    - isort                     (Import sorting)"
    echo "  Linting:"
    echo "    - flake8                    (Style guide enforcement)"
    echo "    - pylint                    (Code analysis)"
    echo "  Security:"
    echo "    - bandit                    (Security issues detection)"
    echo "    - detect-secrets            (Credential scanning)"
    echo "  Type Checking:"
    echo "    - mypy                      (Static type checking)"
    echo "  General Checks:"
    echo "    - trailing-whitespace       (Remove trailing whitespace)"
    echo "    - end-of-file-fixer         (Fix end of file newlines)"
    echo "    - check-yaml                (Validate YAML syntax)"
    echo "    - check-json                (Validate JSON syntax)"
    echo "    - check-toml                (Validate TOML syntax)"
    echo "    - check-added-large-files   (Detect large file additions)"
    echo "    - check-merge-conflict      (Detect merge conflicts)"
    echo "  Python-specific:"
    echo "    - check-docstring-first     (Docstring positioning)"
    echo "    - debug-statements          (Debug code detection)"
    echo "    - name-tests-test           (Test file naming validation)"
    echo ""
    echo "Configuration files:"
    echo "  - .pre-commit-config.yaml     (Main pre-commit configuration)"
    echo "  - .flake8                     (Flake8 settings)"
    echo "  - .pylintrc                   (Pylint settings)"
    echo "  - .bandit                     (Bandit settings)"
    echo "  - pyproject.toml              (Black, isort, mypy settings)"
    echo "  - .secrets.baseline           (Detect-secrets baseline)"
    echo ""
    print_success "Happy coding!"
}

# Run main function
main "$@"
