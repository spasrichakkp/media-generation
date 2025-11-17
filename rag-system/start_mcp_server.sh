#!/bin/bash
# 
# MCP RAG Server Startup Script
# 
# This script starts the RAG system MCP server for integration with Cline.
# It handles environment setup and ensures proper execution.

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory (where this script is located)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check if we're in the right directory
if [ ! -f "mcp_rag_server.py" ]; then
    echo -e "${RED}Error: mcp_rag_server.py not found in current directory${NC}" >&2
    echo "Please run this script from the rag-system directory" >&2
    exit 1
fi

# Check if uv is available
if ! command -v uv &> /dev/null; then
    echo -e "${RED}uv is required but not installed${NC}" >&2
    echo "Install uv with: curl -LsSf https://astral.sh/uv/install.sh | sh" >&2
    exit 1
fi

# Function to log messages
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

# Check if dependencies are installed
log_info "Checking dependencies..."

if [ ! -d ".venv" ]; then
    log_warning "Virtual environment (.venv) not found, installing dependencies..."
    ./setup.sh || {
        log_error "Failed to setup dependencies"
        exit 1
    }
fi

# Function to start MCP server
start_mcp_server() {
    log_info "Starting RAG MCP Server..."
    log_info "Server will listen for MCP protocol requests on stdin/stdout"
    log_info "Available tools: search_codebase, build_context, get_codebase_stats, index_directory"
    log_info "Press Ctrl+C to stop"
    
    python mcp_rag_server.py
}

# Function to start in test mode
start_test_mode() {
    log_info "Running MCP server tests..."
    python mcp_rag_server.py test
}

# Main execution
case "${1:-run}" in
    "run"|"start")
        start_mcp_server
        ;;
    "test")
        start_test_mode
        ;;
    "install")
        log_info "Installing RAG system dependencies..."
        ./setup.sh
        ;;
    "index")
        log_info "Starting indexing process..."
        if command -v uv &> /dev/null; then
            uv run rag-index --full
        else
            python -m indexer.index_all --full
        fi
        ;;
    "search")
        if [ -z "$2" ]; then
            log_error "Usage: $0 search \"your query here\""
            exit 1
        fi
        log_info "Searching for: $2"
        if command -v uv &> /dev/null; then
            uv run rag-search "$2"
        else
            python -m cli.search "$2"
        fi
        ;;
    "api")
        log_info "Starting API server..."
        if command -v uv &> /dev/null; then
            uv run rag-serve
        else
            python -m api.main
        fi
        ;;
    "help"|"-h"|"--help")
        echo "Usage: $0 [command]"
        echo ""
        echo "Commands:"
        echo "  run/start    Start MCP server (default)"
        echo "  test         Run MCP server tests"
        echo "  install      Install dependencies"
        echo "  index        Run full indexing of codebase"
        echo "  search \"q\"   Search codebase with query"
        echo "  api          Start API server instead of MCP"
        echo "  help         Show this help message"
        echo ""
        echo "Examples:"
        echo "  $0                    # Start MCP server"
        echo "  $0 test              # Run tests"
        echo "  $0 search \"How to create job\"  # Quick search"
        echo "  $0 index             # Index the codebase"
        ;;
    *)
        log_error "Unknown command: $1"
        echo "Use '$0 help' for available commands"
        exit 1
        ;;
esac