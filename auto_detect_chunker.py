#!/usr/bin/env python3
"""
Auto Detect Chunker
==================
A standalone, dependency-free utility that intelligently breaks down long task descriptions or text
into memory-optimized chunks suitable for LLM processing.  This module is **self-contained** and can
be imported by `workflow_memory_intelligence_fixed.IntelligentTaskChunker`.

Design goals
------------
1. Handle *any* input length without crashing or rejecting the request.
2. Produce **≤ 10** chunks whenever possible, with a hard upper-bound of 15 as a safety-net.
3. Try to keep chunk sizes between `min_chunk_size` and `max_chunk_size` (defaults: 200-1000 chars).
4. Preserve sentence / paragraph boundaries so that every chunk remains semantically coherent.
5. Return a small analysis dictionary that downstream code can log for observability.

Typical usage
-------------
```python
from auto_detect_chunker import AutoDetectChunker
chunker = AutoDetectChunker()
chunks, analysis = chunker.auto_chunk(long_text)
```
"""
from __future__ import annotations
import math
import re
from typing import List, Tuple, Dict, Any, Optional


class AutoDetectChunker:
    """Intelligently split text into memory-friendly chunks."""

    SENTENCE_END_REGEX = re.compile(r"(?<=[.!?])\s+")

    def __init__(self, *, min_chunk_size: int = 200, max_chunk_size: int = 1000, max_chunks: int = 10):
        if min_chunk_size < 50:
            raise ValueError("min_chunk_size too small – must be ≥ 50")
        if max_chunk_size <= min_chunk_size:
            raise ValueError("max_chunk_size must be > min_chunk_size")
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        self.max_chunks = max_chunks

    # ---------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------
    def auto_chunk(self, text: str) -> Tuple[List[str], Dict[str, Any]]:
        """Return (chunks, analysis) for *text*.

        The algorithm follows three passes:
        1. Quick exit for short texts (< max_chunk_size) – single chunk.
        2. Greedy paragraph merge respecting the size boundaries.
        3. If the result still exceeds *max_chunks*, fall back to sentence-level
           splitting using an adaptive chunk size.
        """
        if not isinstance(text, str):
            raise TypeError("text must be str")
        original_len = len(text)
        if original_len == 0:
            return [""], self._analysis(original_len, [""])

        # 1. Fast path
        if original_len <= self.max_chunk_size:
            return [text], self._analysis(original_len, [text])

        # 2. Paragraph-level greedy grouping
        paragraphs = self._split_paragraphs(text)
        chunks = self._greedy_group(paragraphs)

        # 3. If still too many chunks, use sentence-level adaptive grouping
        if len(chunks) > self.max_chunks:
            sentences = self._split_sentences(text)
            # Compute adaptive chunk size trying to keep chunks ≤ max_chunks
            adaptive_size = max(self.min_chunk_size, min(self.max_chunk_size, math.ceil(original_len / self.max_chunks)))
            chunks = self._greedy_group(sentences, adaptive_size)

        # Final safety – merge last chunks if we still exceed hard limit (15)
        while len(chunks) > self.max_chunks + 5:  # hard upper-bound 15
            # Merge the last two chunks
            chunks[-2] += " " + chunks[-1]
            chunks.pop()

        return chunks, self._analysis(original_len, chunks)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _split_paragraphs(self, text: str) -> List[str]:
        """Split by blank lines keeping non-empty parts."""
        return [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]

    def _split_sentences(self, text: str) -> List[str]:
        """Naïve sentence splitter using punctuation boundaries."""
        sentences = re.split(self.SENTENCE_END_REGEX, text)
        return [s.strip() for s in sentences if s.strip()]

    def _greedy_group(self, parts: List[str], optimal_size: Optional[int] = None) -> List[str]:
        """Greedy grouping of *parts* to approach *optimal_size* per chunk."""
        if optimal_size is None:
            optimal_size = self.max_chunk_size
        chunks: List[str] = []
        current = []
        current_len = 0
        for part in parts:
            part_len = len(part)
            # If a single part is bigger than max – split brutally to stay within limits
            if part_len > self.max_chunk_size:
                # flush current first
                if current:
                    chunks.append("\n".join(current).strip())
                    current = []
                    current_len = 0
                split_point = self.max_chunk_size
                start = 0
                while start < part_len:
                    chunks.append(part[start:start + self.max_chunk_size])
                    start += self.max_chunk_size
                continue

            if current_len + part_len + 1 <= optimal_size:
                current.append(part)
                current_len += part_len + 1  # +1 newline/space
            else:
                chunks.append("\n".join(current).strip())
                current = [part]
                current_len = part_len
        if current:
            chunks.append("\n".join(current).strip())
        return chunks

    def _analysis(self, original_len: int, chunks: List[str]) -> Dict[str, Any]:
        """Return analysis dict used by upstream logging."""
        avg_chunk = sum(len(c) for c in chunks) / len(chunks)
        structure_complexity = len(chunks) + avg_chunk / 1000  # crude metric
        return {
            "original_length": original_len,
            "num_chunks": len(chunks),
            "avg_chunk_size": avg_chunk,
            "optimal_chunk_size": math.ceil(original_len / max(1, len(chunks))),
            "strategy_used": "auto_detect_paragraph_sentence_greedy",
            "structure_complexity": structure_complexity,
        }


# Quick CLI test ---------------------------------------------------------
if __name__ == "__main__":
    import json, sys

    payload = sys.stdin.read() if not sys.stdin.isatty() else ( "\n".join(sys.argv[1:]) or "(empty)" )
    chunker = AutoDetectChunker()
    chunks, analysis = chunker.auto_chunk(payload)
    print(json.dumps({"chunks": chunks, "analysis": analysis}, indent=2))
