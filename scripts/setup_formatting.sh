#!/bin/bash
# Setup script for code formatting tools

echo "🔧 Setting up code formatting tools for AI System Monorepo..."

# Install Python formatting tools
echo "📦 Installing Python formatting tools..."
pip install black isort flake8 mypy pre-commit

# Install Node.js tools for JSON/YAML/Markdown (optional)
if command -v npm &> /dev/null; then
    echo "📦 Installing Prettier for JSON/YAML/Markdown formatting..."
    npm install -g prettier
else
    echo "⚠️  npm not found. Prettier for JSON/YAML/Markdown formatting will not be available."
    echo "   To install: Visit https://nodejs.org/ to install Node.js"
fi

# Setup pre-commit hooks
echo "🔗 Setting up pre-commit hooks..."
pre-commit install

# Run initial formatting
echo "🔧 Running initial code formatting..."
python scripts/format_code.py

echo "✅ Formatting setup complete!"
echo ""
echo "📋 Available commands:"
echo "  - Format code:     python scripts/format_code.py"
echo "  - Format JSON/MD:  prettier --write '**/*.{json,yaml,yml,md}'"
echo "  - Run pre-commit:  pre-commit run --all-files"
echo ""
echo "🚀 Your code will now be automatically formatted on commit!" 