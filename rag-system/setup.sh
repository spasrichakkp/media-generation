#!/usr/bin/env bash
#
# RAG System Setup Script
# Sets up the RAG system using uv for fast dependency management
#
# Usage:
#   ./setup.sh              # Basic setup
#   ./setup.sh --full       # Install with all optional dependencies
#   ./setup.sh --gpu        # Install with GPU support
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Functions
log_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

log_success() {
    echo -e "${GREEN}✓${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
}

print_header() {
    echo ""
    echo "=================================="
    echo "$1"
    echo "=================================="
    echo ""
}

# Check if uv is installed
check_uv() {
    print_header "Checking UV Installation"

    if ! command -v uv &> /dev/null; then
        log_error "uv is not installed"
        echo ""
        echo "Install uv with:"
        echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
        echo ""
        echo "Or visit: https://github.com/astral-sh/uv"
        exit 1
    fi

    UV_VERSION=$(uv --version 2>&1 || echo "unknown")
    log_success "uv is installed: $UV_VERSION"
}

# Check Python version
check_python() {
    print_header "Checking Python Version"

    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is not installed"
        exit 1
    fi

    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

    if [ "$PYTHON_MAJOR" -lt 3 ] || [ "$PYTHON_MAJOR" -eq 3 -a "$PYTHON_MINOR" -lt 11 ]; then
        log_error "Python 3.11+ is required (found: $PYTHON_VERSION)"
        exit 1
    fi

    log_success "Python version OK: $PYTHON_VERSION"
}

# Create data directories
create_directories() {
    print_header "Creating Data Directories"

    mkdir -p data/chroma
    mkdir -p data/cache
    mkdir -p data/logs

    log_success "Created data directories"
}

# Install dependencies
install_dependencies() {
    local INSTALL_TYPE=$1

    print_header "Installing Dependencies with UV"

    case $INSTALL_TYPE in
        "full")
            log_info "Installing with all optional dependencies..."
            uv pip install -e ".[dev,full]"
            ;;
        "gpu")
            log_info "Installing with GPU support..."
            uv pip install -e ".[dev,gpu]"
            ;;
        *)
            log_info "Installing base dependencies..."
            uv pip install -e ".[dev]"
            ;;
    esac

    log_success "Dependencies installed"
}

# Download embedding models
download_models() {
    print_header "Downloading Embedding Models"

    log_info "Downloading sentence-transformers model..."

    python3 -c "
from sentence_transformers import SentenceTransformer
import sys

try:
    print('Downloading all-MiniLM-L6-v2...')
    model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
    print('Model downloaded successfully!')
except Exception as e:
    print(f'Error downloading model: {e}', file=sys.stderr)
    sys.exit(1)
" && log_success "Model downloaded" || log_warning "Model download failed (will download on first use)"
}

# Create config if not exists
setup_config() {
    print_header "Setting Up Configuration"

    if [ ! -f "config.yaml" ]; then
        log_warning "config.yaml not found (using defaults)"
    else
        log_success "config.yaml found"
    fi

    # Create .env if not exists
    if [ ! -f ".env" ]; then
        log_info "Creating .env file..."
        cat > .env << 'EOF'
# RAG System Environment Variables

# Embedding Model
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
EMBEDDING_DEVICE=cpu

# Vector Store
VECTOR_STORE_TYPE=chromadb
CHROMA_PERSIST_DIR=./data/chroma

# Redis (optional - for caching)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=1

# API
API_HOST=0.0.0.0
API_PORT=8001

# Logging
LOG_LEVEL=INFO
EOF
        log_success "Created .env file"
    else
        log_success ".env file exists"
    fi
}

# Run quick test
run_test() {
    print_header "Running Quick Test"

    log_info "Testing CLI search (with mock data)..."

    if uv run python cli/search.py "test query" --format json > /dev/null 2>&1; then
        log_success "CLI test passed"
    else
        log_warning "CLI test failed (expected if not indexed yet)"
    fi
}

# Print next steps
print_next_steps() {
    print_header "Setup Complete!"

    echo "Next steps:"
    echo ""
    echo "1. Index your codebase:"
    echo "   ${GREEN}uv run python indexer/index_all.py --full${NC}"
    echo ""
    echo "2. Search the codebase:"
    echo "   ${GREEN}uv run rag-search \"How to create a job?\"${NC}"
    echo ""
    echo "3. Start the API server:"
    echo "   ${GREEN}uv run uvicorn api.main:app --host 0.0.0.0 --port 8001${NC}"
    echo ""
    echo "4. For incremental updates:"
    echo "   ${GREEN}uv run python indexer/index_all.py --incremental${NC}"
    echo ""
    echo "5. For watch mode (auto-reindex on changes):"
    echo "   ${GREEN}uv run python indexer/index_all.py --watch${NC}"
    echo ""
    echo "Documentation:"
    echo "  • README.md - System overview"
    echo "  • ../docs/RAG_BEST_PRACTICES.md - Implementation guide"
    echo "  • config.yaml - Configuration reference"
    echo ""
    echo "Useful commands:"
    echo "  ${BLUE}uv run rag-search \"query\" --help${NC}    # Show search options"
    echo "  ${BLUE}uv run python indexer/index_all.py --help${NC}  # Show index options"
    echo ""
}

# Main execution
main() {
    local INSTALL_TYPE="base"

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --full)
                INSTALL_TYPE="full"
                shift
                ;;
            --gpu)
                INSTALL_TYPE="gpu"
                shift
                ;;
            --help|-h)
                echo "Usage: ./setup.sh [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --full    Install with all optional dependencies"
                echo "  --gpu     Install with GPU support (CUDA)"
                echo "  --help    Show this help message"
                echo ""
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                echo "Use --help for usage information"
                exit 1
                ;;
        esac
    done

    # Run setup steps
    check_uv
    check_python
    create_directories
    install_dependencies "$INSTALL_TYPE"
    setup_config
    download_models
    run_test
    print_next_steps

    log_success "RAG System is ready to use!"
}

# Run main
main "$@"
