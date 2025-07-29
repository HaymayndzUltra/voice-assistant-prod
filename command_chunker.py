#!/usr/bin/env python3
"""
Command Chunker - Splits long commands into 2-3 manageable chunks
Ginagamit para sa mga mahabang command na kailangan hatiin
"""

import re
import sys
import argparse
from typing import List, Tuple

class CommandChunker:
    def __init__(self, max_chunk_size: int = 1000):
        self.max_chunk_size = max_chunk_size
        
    def analyze_command_size(self, command: str) -> str:
        """Analyze command size and recommend chunking strategy"""
        length = len(command)
        
        if length <= self.max_chunk_size:
            return "SMALL - No chunking needed"
        elif length <= self.max_chunk_size * 2:
            return "MEDIUM - Split into 2 chunks"
        else:
            return "LARGE - Split into 3 chunks"
    
    def smart_chunk_by_operators(self, command: str) -> List[str]:
        """Chunk command intelligently by operators and logical breaks"""
        # Common command separators and operators
        separators = [
            ' && ',  # AND operator
            ' || ',  # OR operator  
            ' ; ',   # Command separator
            ' | ',   # Pipe operator
            ' > ',   # Redirect output
            ' >> ',  # Append output
            ' < ',   # Input redirect
        ]
        
        chunks = []
        current_chunk = ""
        
        # Split by separators while preserving them
        parts = [command]
        for sep in separators:
            new_parts = []
            for part in parts:
                if sep in part:
                    split_parts = part.split(sep)
                    for i, sp in enumerate(split_parts):
                        if i > 0:
                            new_parts.append(sep)
                        new_parts.append(sp)
                else:
                    new_parts.append(part)
            parts = new_parts
        
        # Group parts into chunks
        for part in parts:
            if len(current_chunk + part) <= self.max_chunk_size:
                current_chunk += part
            else:
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                current_chunk = part
        
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
            
        return chunks
    
    def chunk_by_size(self, command: str, num_chunks: int) -> List[str]:
        """Simple size-based chunking"""
        chunk_size = len(command) // num_chunks
        chunks = []
        
        for i in range(num_chunks):
            start = i * chunk_size
            if i == num_chunks - 1:  # Last chunk gets remainder
                end = len(command)
            else:
                end = (i + 1) * chunk_size
                # Try to break at word boundary
                while end < len(command) and command[end] != ' ':
                    end += 1
            
            chunk = command[start:end].strip()
            if chunk:
                chunks.append(chunk)
        
        return chunks
    
    def chunk_by_arguments(self, command: str) -> List[str]:
        """Chunk by command arguments and flags"""
        # Split by common argument patterns
        parts = re.split(r'(\s+--?\w+)', command)
        
        chunks = []
        current_chunk = ""
        
        for part in parts:
            if len(current_chunk + part) <= self.max_chunk_size:
                current_chunk += part
            else:
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                current_chunk = part
        
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
            
        return chunks
    
    def chunk_command(self, command: str, strategy: str = "auto") -> List[str]:
        """Main chunking function with different strategies"""
        command = command.strip()
        
        if len(command) <= self.max_chunk_size:
            return [command]
        
        if strategy == "auto":
            # Try smart chunking first
            chunks = self.smart_chunk_by_operators(command)
            if len(chunks) <= 3 and all(len(c) <= self.max_chunk_size * 1.2 for c in chunks):
                return chunks
            
            # Fallback to argument-based chunking
            chunks = self.chunk_by_arguments(command)
            if len(chunks) <= 3 and all(len(c) <= self.max_chunk_size * 1.2 for c in chunks):
                return chunks
        
        elif strategy == "operators":
            return self.smart_chunk_by_operators(command)
        
        elif strategy == "arguments":
            return self.chunk_by_arguments(command)
        
        elif strategy == "size":
            # Determine number of chunks based on size
            if len(command) <= self.max_chunk_size * 2:
                return self.chunk_by_size(command, 2)
            else:
                return self.chunk_by_size(command, 3)
        
        # Default size-based chunking
        num_chunks = min(3, max(2, len(command) // self.max_chunk_size + 1))
        return self.chunk_by_size(command, num_chunks)
    
    def format_output(self, chunks: List[str], output_format: str = "numbered") -> str:
        """Format the chunked output"""
        if output_format == "numbered":
            result = f"Command split into {len(chunks)} chunks:\n\n"
            for i, chunk in enumerate(chunks, 1):
                result += f"=== CHUNK {i} ===\n{chunk}\n\n"
            return result
        
        elif output_format == "script":
            result = "#!/bin/bash\n# Generated chunks\n\n"
            for i, chunk in enumerate(chunks, 1):
                result += f"# Chunk {i}\n{chunk}\n\n"
            return result
        
        elif output_format == "json":
            import json
            return json.dumps({
                "total_chunks": len(chunks),
                "chunks": chunks,
                "original_length": sum(len(c) for c in chunks)
            }, indent=2)
        
        else:  # plain
            return "\n".join(chunks)

def main():
    parser = argparse.ArgumentParser(description="Chunk long commands into manageable pieces")
    parser.add_argument("command", nargs="?", help="Command to chunk (or use stdin)")
    parser.add_argument("-s", "--strategy", choices=["auto", "operators", "arguments", "size"], 
                       default="auto", help="Chunking strategy")
    parser.add_argument("-m", "--max-size", type=int, default=1000, 
                       help="Maximum chunk size (default: 1000)")
    parser.add_argument("-f", "--format", choices=["numbered", "script", "json", "plain"],
                       default="numbered", help="Output format")
    parser.add_argument("-a", "--analyze", action="store_true", 
                       help="Only analyze without chunking")
    
    args = parser.parse_args()
    
    # Get command from argument or stdin
    if args.command:
        command = args.command
    else:
        command = sys.stdin.read().strip()
    
    if not command:
        print("Error: No command provided!")
        sys.exit(1)
    
    chunker = CommandChunker(max_chunk_size=args.max_size)
    
    # Analysis mode
    if args.analyze:
        analysis = chunker.analyze_command_size(command)
        print(f"Command length: {len(command)} characters")
        print(f"Analysis: {analysis}")
        return
    
    # Chunk the command
    chunks = chunker.chunk_command(command, strategy=args.strategy)
    
    # Output results
    output = chunker.format_output(chunks, output_format=args.format)
    print(output)

# Interactive mode functions
def interactive_mode():
    """Interactive command chunking"""
    chunker = CommandChunker()
    
    print("=== COMMAND CHUNKER - INTERACTIVE MODE ===")
    print("Paste your long command below (Ctrl+D to finish):")
    
    try:
        lines = []
        while True:
            try:
                line = input()
                lines.append(line)
            except EOFError:
                break
        
        command = " ".join(lines).strip()
        
        if not command:
            print("No command entered!")
            return
        
        print(f"\nOriginal command length: {len(command)} characters")
        print(f"Analysis: {chunker.analyze_command_size(command)}\n")
        
        # Try different strategies
        strategies = ["auto", "operators", "arguments", "size"]
        
        for strategy in strategies:
            print(f"=== STRATEGY: {strategy.upper()} ===")
            chunks = chunker.chunk_command(command, strategy=strategy)
            output = chunker.format_output(chunks, "numbered")
            print(output)
        
    except KeyboardInterrupt:
        print("\nOperation cancelled.")

if __name__ == "__main__":
    if len(sys.argv) == 1:
        # No arguments, start interactive mode
        interactive_mode()
    else:
        main()
