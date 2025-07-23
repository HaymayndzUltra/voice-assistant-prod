#!/usr/bin/env python3
"""
Markdown formatting script specifically for the AI System Monorepo.
This script formats Markdown files using Prettier with custom settings.
"""

import subprocess
import sys
from pathlib import Path
import json

def create_custom_prettier_config(config_options: dict) -> str:
    """Create a temporary prettier config file with custom options."""
    config_file = Path(".prettierrc.temp.json")
    
    # Base config for Markdown
    base_config = {
        "printWidth": config_options.get("line_width", 120),
        "tabWidth": config_options.get("indent_size", 2),
        "useTabs": config_options.get("use_tabs", False),
        "proseWrap": config_options.get("wrap_style", "preserve"),
        "endOfLine": "lf",
        "overrides": [
            {
                "files": "*.md",
                "options": {
                    "printWidth": config_options.get("line_width", 120),
                    "proseWrap": config_options.get("wrap_style", "preserve"),
                    "tabWidth": config_options.get("indent_size", 2)
                }
            }
        ]
    }
    
    with open(config_file, 'w') as f:
        json.dump(base_config, f, indent=2)
    
    return str(config_file)

def format_markdown_files(target_files: list = None, custom_config: dict = None):
    """Format Markdown files with optional custom configuration."""
    
    if custom_config:
        config_file = create_custom_prettier_config(custom_config)
        config_arg = ["--config", config_file]
    else:
        config_arg = []
    
    # If no specific files provided, format all .md files
    if not target_files:
        print("🔍 Finding all Markdown files...")
        result = subprocess.run(
            ["find", ".", "-name", "*.md", "-not", "-path", "./whisper.cpp/*", "-not", "-path", "./logs/*"],
            capture_output=True, text=True
        )
        target_files = result.stdout.strip().split('\n') if result.stdout.strip() else []
    
    if not target_files:
        print("❌ No Markdown files found to format")
        return False
    
    print(f"📝 Formatting {len(target_files)} Markdown files...")
    
    try:
        # Run prettier on the files
        cmd = ["prettier", "--write"] + config_arg + target_files
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("✅ Markdown formatting completed successfully!")
        
        # Clean up temp config if created
        if custom_config:
            Path(config_file).unlink(missing_ok=True)
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Prettier formatting failed: {e.stderr}")
        # Clean up temp config if created
        if custom_config:
            Path(config_file).unlink(missing_ok=True)
        return False
    except FileNotFoundError:
        print("❌ Prettier not found! Install with: npm install -g prettier")
        return False

def main():
    """Main function with formatting options."""
    print("🔧 Markdown Formatting Tool for AI System Monorepo")
    print("")
    
    # Check command line arguments for custom options
    if len(sys.argv) > 1:
        if sys.argv[1] == "--help":
            print("Usage: python scripts/format_markdown.py [options]")
            print("")
            print("Options:")
            print("  --help              Show this help message")
            print("  --line-width 120    Set maximum line width (default: 120)")
            print("  --wrap never        Set prose wrap style: 'always', 'never', 'preserve' (default: preserve)")
            print("  --indent 2          Set indentation size (default: 2)")
            print("  --tabs              Use tabs instead of spaces")
            print("  --files file1.md file2.md  Format specific files")
            print("")
            print("Examples:")
            print("  python scripts/format_markdown.py")
            print("  python scripts/format_markdown.py --line-width 100 --wrap always")
            print("  python scripts/format_markdown.py --files README.md CHANGELOG.md")
            return 0
        
        # Parse custom options
        custom_config = {}
        target_files = None
        i = 1
        
        while i < len(sys.argv):
            if sys.argv[i] == "--line-width" and i + 1 < len(sys.argv):
                custom_config["line_width"] = int(sys.argv[i + 1])
                i += 2
            elif sys.argv[i] == "--wrap" and i + 1 < len(sys.argv):
                custom_config["wrap_style"] = sys.argv[i + 1]
                i += 2
            elif sys.argv[i] == "--indent" and i + 1 < len(sys.argv):
                custom_config["indent_size"] = int(sys.argv[i + 1])
                i += 2
            elif sys.argv[i] == "--tabs":
                custom_config["use_tabs"] = True
                i += 1
            elif sys.argv[i] == "--files":
                target_files = []
                i += 1
                while i < len(sys.argv) and not sys.argv[i].startswith("--"):
                    target_files.append(sys.argv[i])
                    i += 1
            else:
                i += 1
        
        success = format_markdown_files(target_files, custom_config if custom_config else None)
    else:
        # Use default configuration
        success = format_markdown_files()
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main()) 