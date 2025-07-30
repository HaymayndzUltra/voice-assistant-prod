#!/usr/bin/env python3
"""
Auto-Detecting Command Chunker - Automatically determines optimal chunk size and strategy
"""

import re
import sys
import argparse
from typing import List, Tuple, Dict, Any
import math

class AutoDetectChunker:
    """TODO: Add description for AutoDetectChunker."""
    def __init__(self, min_chunk_size: int = 300, max_chunk_size: int = 1500):
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size

    def analyze_content_structure(self, content: str) -> Dict[str, Any]:
        """Analyze content structure to determine optimal chunking approach"""
        lines = content.split('\n')

        analysis = {
            'total_length': len(content),
            'total_lines': len(lines),
            'has_headers': False,
            'has_bullets': False,
            'has_yaml_structure': False,
            'has_code_blocks': False,
            'has_long_paragraphs': False,
            'avg_line_length': 0,
            'structure_complexity': 0,
            'recommended_strategy': 'sections',
            'optimal_chunk_size': 800
        }

        # Analyze line lengths
        line_lengths = [len(line) for line in lines if line.strip()]
        analysis['avg_line_length'] = sum(line_lengths) / max(len(line_lengths), 1)

        # Check for various structures
        header_count = 0
        bullet_count = 0
        yaml_indicators = 0
        code_block_count = 0
        long_paragraph_count = 0

        for line in lines:
            stripped = line.strip()

            # Headers (markdown style)
            if re.match(r'^#+\s', stripped):
                header_count += 1
                analysis['has_headers'] = True

            # Bullet points
            if re.match(r'^[-*•]\s', stripped) or re.match(r'^\s+[-*•]\s', stripped):
                bullet_count += 1
                analysis['has_bullets'] = True

            # YAML structure indicators
            if ':' in stripped and (stripped.endswith(':') or re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*:', stripped)):
                yaml_indicators += 1
                analysis['has_yaml_structure'] = True

            # Code blocks
            if stripped.startswith('```') or stripped.startswith('    ') and len(stripped) > 4:
                code_block_count += 1
                analysis['has_code_blocks'] = True

            # Long paragraphs
            if len(stripped) > 200 and not stripped.startswith(('-', '*', '#', '•')):
                long_paragraph_count += 1
                analysis['has_long_paragraphs'] = True

        # Calculate structure complexity
        analysis['structure_complexity'] = (
            header_count * 3 +
            bullet_count * 2 +
            yaml_indicators * 1.5 +
            code_block_count * 2 +
            long_paragraph_count * 1
        ) / max(len(lines), 1)

        # Determine optimal chunk size based on analysis
        analysis['optimal_chunk_size'] = self._calculate_optimal_chunk_size(analysis)

        # Determine best strategy
        analysis['recommended_strategy'] = self._determine_strategy(analysis)

        return analysis

    def _calculate_optimal_chunk_size(self, analysis: Dict[str, Any]) -> int:
        """Calculate optimal chunk size based on content analysis"""
        base_size = 800

        # Adjust based on content length
        if analysis['total_length'] < 1000:
            base_size = min(analysis['total_length'], 500)
        elif analysis['total_length'] > 5000:
            base_size = 1200

        # Adjust based on structure complexity
        if analysis['structure_complexity'] > 0.3:  # High complexity
            base_size = int(base_size * 0.8)  # Smaller chunks for complex content
        elif analysis['structure_complexity'] < 0.1:  # Low complexity
            base_size = int(base_size * 1.2)  # Larger chunks for simple content

        # Adjust based on average line length
        if analysis['avg_line_length'] > 100:  # Long lines
            base_size = int(base_size * 1.1)
        elif analysis['avg_line_length'] < 50:  # Short lines
            base_size = int(base_size * 0.9)

        # Ensure within bounds
        return max(self.min_chunk_size, min(self.max_chunk_size, base_size))

    def _determine_strategy(self, analysis: Dict[str, Any]) -> str:
        """Determine best chunking strategy based on content analysis"""
        if analysis['has_headers'] and analysis['structure_complexity'] > 0.2:
            return 'headers'
        elif analysis['has_bullets'] and analysis['structure_complexity'] > 0.15:
            return 'bullets'
        elif analysis['has_yaml_structure']:
            return 'yaml'
        elif analysis['has_code_blocks']:
            return 'code'
        else:
            return 'smart'

    def chunk_by_yaml_structure(self, content: str, max_chunk_size: int) -> List[str]:
        """Chunk by YAML structure (keys, nested sections)"""
        chunks = []
        current_chunk = ""

        lines = content.split('\n')
        current_indent = 0

        for line in lines:
            line_with_newline = line + '\n'

            # Calculate indentation level
            indent = len(line) - len(line.lstrip())

            # Check if this is a main key (no or low indentation with colon)
            is_main_key = indent <= 2 and ':' in line and (line.strip().endswith(':') or re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*:', line.strip()))

            # If we hit a main key and current chunk is getting large
            if is_main_key and len(current_chunk) > max_chunk_size * 0.7:
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                    current_chunk = ""

            # Check if adding this line would exceed chunk size
            if len(current_chunk + line_with_newline) > max_chunk_size:
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                current_chunk = line_with_newline
            else:
                current_chunk += line_with_newline

        # Add remaining chunk
        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return chunks

    def chunk_by_code_blocks(self, content: str, max_chunk_size: int) -> List[str]:
        """Chunk by code blocks and sections"""
        chunks = []
        current_chunk = ""
        in_code_block = False

        lines = content.split('\n')

        for line in lines:
            line_with_newline = line + '\n'

            # Track code block boundaries
            if line.strip().startswith('```'):
                in_code_block = not in_code_block

            # Don't break inside code blocks
            if not in_code_block and len(current_chunk + line_with_newline) > max_chunk_size:
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                current_chunk = line_with_newline
            else:
                current_chunk += line_with_newline

        # Add remaining chunk
        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return chunks

    def chunk_by_headers(self, content: str, max_chunk_size: int) -> List[str]:
        """Chunk by markdown headers"""
        chunks = []
        current_chunk = ""

        lines = content.split('\n')

        for line in lines:
            line_with_newline = line + '\n'

            # Check if this is a header
            is_header = re.match(r'^#+\s', line.strip())

            # If we hit a header and current chunk has content
            if is_header and current_chunk.strip():
                chunks.append(current_chunk.strip())
                current_chunk = line_with_newline
            elif len(current_chunk + line_with_newline) > max_chunk_size:
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                current_chunk = line_with_newline
            else:
                current_chunk += line_with_newline

        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return chunks

    def chunk_by_bullets(self, content: str, max_chunk_size: int) -> List[str]:
        """Chunk by bullet points with hierarchy awareness"""
        chunks = []
        current_chunk = ""

        lines = content.split('\n')

        for line in lines:
            line_with_newline = line + '\n'

            # Check if this is a main bullet point (low indentation)
            is_main_bullet = re.match(r'^[-*•]\s', line.strip()) and len(line) - len(line.lstrip()) <= 4

            # If we hit a main bullet and current chunk is getting large
            if is_main_bullet and len(current_chunk) > max_chunk_size * 0.7:
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                    current_chunk = ""

            # Check if adding this line would exceed chunk size
            if len(current_chunk + line_with_newline) > max_chunk_size:
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                current_chunk = line_with_newline
            else:
                current_chunk += line_with_newline

        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return chunks

    def smart_chunk(self, content: str, max_chunk_size: int) -> List[str]:
        """Smart chunking with multiple strategies"""
        chunks = []
        current_chunk = ""

        # Split by natural boundaries (paragraphs, sentences)
        paragraphs = content.split('\n\n')

        for paragraph in paragraphs:
            paragraph_with_breaks = paragraph + '\n\n'

            if len(current_chunk + paragraph_with_breaks) <= max_chunk_size:
                current_chunk += paragraph_with_breaks
            else:
                # Current paragraph won't fit, save current chunk
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())

                # If paragraph itself is too long, split it further
                if len(paragraph_with_breaks) > max_chunk_size:
                    # Split by sentences
                    sentences = re.split(r'[.!?]+\s+', paragraph)
                    temp_chunk = ""

                    for sentence in sentences:
                        sentence = sentence.strip()
                        if not sentence:
                            continue

                        sentence_with_period = sentence + '. '

                        if len(temp_chunk + sentence_with_period) <= max_chunk_size:
                            temp_chunk += sentence_with_period
                        else:
                            if temp_chunk.strip():
                                chunks.append(temp_chunk.strip())
                            temp_chunk = sentence_with_period

                    current_chunk = temp_chunk + '\n\n'
                else:
                    current_chunk = paragraph_with_breaks

        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return chunks

    def auto_chunk(self, content: str, strategy_override: str = None) -> Tuple[List[str], Dict[str, Any]]:
        """Automatically chunk content with optimal settings"""
        # Analyze content
        analysis = self.analyze_content_structure(content)

        # Use override strategy if provided
        strategy = strategy_override or analysis['recommended_strategy']
        chunk_size = analysis['optimal_chunk_size']

        # Apply chunking strategy
        if strategy == 'headers':
            chunks = self.chunk_by_headers(content, chunk_size)
        elif strategy == 'bullets':
            chunks = self.chunk_by_bullets(content, chunk_size)
        elif strategy == 'yaml':
            chunks = self.chunk_by_yaml_structure(content, chunk_size)
        elif strategy == 'code':
            chunks = self.chunk_by_code_blocks(content, chunk_size)
        else:  # smart
            chunks = self.smart_chunk(content, chunk_size)

        # Update analysis with results
        analysis['actual_chunks'] = len(chunks)
        analysis['actual_chunk_sizes'] = [len(chunk) for chunk in chunks]
        analysis['strategy_used'] = strategy

        return chunks, analysis

    def format_analysis(self, analysis: Dict[str, Any]) -> str:
        """Format analysis results for display"""
        result = "📊 CONTENT ANALYSIS:\n"
        result += "=" * 30 + "\n"
        result += f"Total Length: {analysis['total_length']:,} characters\n"
        result += f"Total Lines: {analysis['total_lines']:,}\n"
        result += f"Avg Line Length: {analysis['avg_line_length']:.1f} chars\n"
        result += f"Structure Complexity: {analysis['structure_complexity']:.2f}\n\n"

        result += "🔍 DETECTED STRUCTURES:\n"
        result += f"• Headers: {'✅' if analysis['has_headers'] else '❌'}\n"
        result += f"• Bullet Points: {'✅' if analysis['has_bullets'] else '❌'}\n"
        result += f"• YAML Structure: {'✅' if analysis['has_yaml_structure'] else '❌'}\n"
        result += f"• Code Blocks: {'✅' if analysis['has_code_blocks'] else '❌'}\n"
        result += f"• Long Paragraphs: {'✅' if analysis['has_long_paragraphs'] else '❌'}\n\n"

        result += "🎯 RECOMMENDATIONS:\n"
        result += f"• Optimal Chunk Size: {analysis['optimal_chunk_size']} characters\n"
        result += f"• Recommended Strategy: {analysis['recommended_strategy']}\n"

        if 'actual_chunks' in analysis:
            result += f"\n📋 CHUNKING RESULTS:\n"
            result += f"• Chunks Created: {analysis['actual_chunks']}\n"
            result += f"• Strategy Used: {analysis['strategy_used']}\n"
            result += f"• Chunk Sizes: {', '.join(map(str, analysis['actual_chunk_sizes']))}\n"

        return result

    def format_output(self, chunks: List[str], output_format: str = "numbered") -> str:
        """Format the chunked output"""
        if output_format == "numbered":
            result = f"Command split into {len(chunks)} chunks:\n\n"
            for i, chunk in enumerate(chunks, 1):
                result += f"=== CHUNK {i} ===\n{chunk}\n\n"
            return result

        elif output_format == "json":
            import json
            return json.dumps({
                "total_chunks": len(chunks),
                "chunks": chunks,
                "chunk_sizes": [len(c) for c in chunks]
            }, indent=2)

        else:  # plain
            return "\n".join(chunks)

def main():
    parser = argparse.ArgumentParser(description="Auto-detecting command chunker")
    parser.add_argument("command", nargs="?", help="Command to chunk (or use stdin)")
    parser.add_argument("-s", "--strategy", choices=["auto", "headers", "bullets", "yaml", "code", "smart"],
                       default="auto", help="Chunking strategy (auto = auto-detect)")
    parser.add_argument("-f", "--format", choices=["numbered", "json", "plain"],
                       default="numbered", help="Output format")
    parser.add_argument("-a", "--analyze", action="store_true",
                       help="Show analysis only without chunking")
    parser.add_argument("--min-size", type=int, default=300, help="Minimum chunk size")
    parser.add_argument("--max-size", type=int, default=1500, help="Maximum chunk size")

    args = parser.parse_args()

    # Get command from argument or stdin
    if args.command:
        command = args.command
    else:
        command = sys.stdin.read().strip()

    if not command:
        print("Error: No command provided!")
        sys.exit(1)

    chunker = AutoDetectChunker(min_chunk_size=args.min_size, max_chunk_size=args.max_size)

    # Auto-chunk with analysis
    strategy = None if args.strategy == "auto" else args.strategy
    chunks, analysis = chunker.auto_chunk(command, strategy_override=strategy)

    # Display analysis
    print(chunker.format_analysis(analysis))

    if not args.analyze:
        print("\n" + "=" * 50)
        output = chunker.format_output(chunks, output_format=args.format)
        print(output)

if __name__ == "__main__":
    main()
