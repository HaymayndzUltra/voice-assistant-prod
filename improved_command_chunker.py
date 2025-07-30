#!/usr/bin/env python3
"""
Improved Command Chunker - Better handling for text-based content
"""

import re
import sys
import argparse
from typing import List, Tuple

class ImprovedCommandChunker:
    """TODO: Add description for ImprovedCommandChunker."""
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

    def smart_chunk_by_sections(self, command: str) -> List[str]:
        """Chunk by logical sections (headers, bullets, etc.)"""
        chunks = []
        current_chunk = ""

        lines = command.split('\n')

        for line in lines:
            line_with_newline = line + '\n'

            # Check if adding this line would exceed chunk size
            if len(current_chunk + line_with_newline) > self.max_chunk_size:
                # If current chunk is not empty, save it
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                    current_chunk = ""

                # If single line is too long, handle it separately
                if len(line_with_newline) > self.max_chunk_size:
                    # Split long line by sentences or clauses
                    sub_chunks = self._split_long_line(line)
                    chunks.extend(sub_chunks)
                else:
                    current_chunk = line_with_newline
            else:
                current_chunk += line_with_newline

        # Add remaining chunk
        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return chunks

    def _split_long_line(self, line: str) -> List[str]:
        """Split a long line by sentences or clauses"""
        # Split by common sentence terminators
        sentences = re.split(r'[.!?]+\s+', line)

        chunks = []
        current_chunk = ""

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            # Add sentence terminator back (except for last sentence)
            if sentence != sentences[-1]:
                sentence += ". "

            if len(current_chunk + sentence) <= self.max_chunk_size:
                current_chunk += sentence
            else:
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                current_chunk = sentence

        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return chunks

    def chunk_by_bullet_points(self, command: str) -> List[str]:
        """Chunk by bullet points and maintain hierarchy"""
        chunks = []
        current_chunk = ""

        lines = command.split('\n')

        for line in lines:
            line_with_newline = line + '\n'

            # Check if this is a main bullet point (starts with -)
            is_main_bullet = line.strip().startswith('- ') and not line.strip().startswith('    -')

            # If we hit a main bullet and current chunk is getting large
            if is_main_bullet and len(current_chunk) > self.max_chunk_size * 0.7:
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                    current_chunk = ""

            # Check if adding this line would exceed chunk size
            if len(current_chunk + line_with_newline) > self.max_chunk_size:
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                current_chunk = line_with_newline
            else:
                current_chunk += line_with_newline

        # Add remaining chunk
        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return chunks

    def chunk_by_headers(self, command: str) -> List[str]:
        """Chunk by markdown headers and sections"""
        chunks = []
        current_chunk = ""

        lines = command.split('\n')

        for line in lines:
            line_with_newline = line + '\n'

            # Check if this is a header (starts with #)
            is_header = line.strip().startswith('#')

            # If we hit a header and current chunk has content
            if is_header and current_chunk.strip():
                chunks.append(current_chunk.strip())
                current_chunk = line_with_newline
            elif len(current_chunk + line_with_newline) > self.max_chunk_size:
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                current_chunk = line_with_newline
            else:
                current_chunk += line_with_newline

        # Add remaining chunk
        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return chunks

    def chunk_command(self, command: str, strategy: str = "smart") -> List[str]:
        """Main chunking function with improved strategies"""
        command = command.strip()

        if len(command) <= self.max_chunk_size:
            return [command]

        if strategy == "smart":
            # Try different strategies and pick the best
            strategies = [
                ("headers", self.chunk_by_headers),
                ("bullets", self.chunk_by_bullet_points),
                ("sections", self.smart_chunk_by_sections)
            ]

            best_chunks = None
            best_score = float('inf')

            for strategy_name, strategy_func in strategies:
                try:
                    chunks = strategy_func(command)
                    # Score based on balance and number of chunks
                    score = self._score_chunks(chunks)

                    if score < best_score:
                        best_score = score
                        best_chunks = chunks

                except Exception:
                    continue

            return best_chunks if best_chunks else [command]

        elif strategy == "headers":
            return self.chunk_by_headers(command)
        elif strategy == "bullets":
            return self.chunk_by_bullet_points(command)
        elif strategy == "sections":
            return self.smart_chunk_by_sections(command)
        else:
            return self.smart_chunk_by_sections(command)

    def _score_chunks(self, chunks: List[str]) -> float:
        """Score chunks based on balance and readability"""
        if not chunks:
            return float('inf')

        # Penalize too many or too few chunks
        chunk_count_penalty = abs(len(chunks) - 3) * 10

        # Penalize unbalanced chunks
        sizes = [len(chunk) for chunk in chunks]
        avg_size = sum(sizes) / len(sizes)
        balance_penalty = sum(abs(size - avg_size) for size in sizes) / len(sizes)

        # Penalize chunks that are too small or too large
        size_penalty = 0
        for size in sizes:
            if size < self.max_chunk_size * 0.3:
                size_penalty += 20
            elif size > self.max_chunk_size * 1.2:
                size_penalty += 50

        return chunk_count_penalty + balance_penalty + size_penalty

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
                "original_length": sum(len(c) for c in chunks),
                "chunk_sizes": [len(c) for c in chunks]
            }, indent=2)

        else:  # plain
            return "\n".join(chunks)

def main():
    parser = argparse.ArgumentParser(description="Improved command chunker for text content")
    parser.add_argument("command", nargs="?", help="Command to chunk (or use stdin)")
    parser.add_argument("-s", "--strategy", choices=["smart", "headers", "bullets", "sections"],
                       default="smart", help="Chunking strategy")
    parser.add_argument("-m", "--max-size", type=int, default=800,
                       help="Maximum chunk size (default: 800)")
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

    chunker = ImprovedCommandChunker(max_chunk_size=args.max_size)

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

if __name__ == "__main__":
    main()
