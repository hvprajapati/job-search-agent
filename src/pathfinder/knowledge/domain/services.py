"""Knowledge domain services — chunking and retrieval."""
from __future__ import annotations
import re


class ChunkingService:
    CHUNK_SIZE = 500
    OVERLAP = 100

    @classmethod
    def chunk(cls, text: str, strategy: str = "semantic") -> list[str]:
        if strategy == "semantic":
            return cls._semantic_chunk(text)
        return cls._fixed_chunk(text)

    @classmethod
    def _semantic_chunk(cls, text: str) -> list[str]:
        paragraphs = re.split(r"\n\s*\n", text)
        chunks: list[str] = []
        current = ""
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            if len(current) + len(para) < cls.CHUNK_SIZE:
                current += ("\n\n" if current else "") + para
            else:
                if current:
                    chunks.append(current)
                current = para
        if current:
            chunks.append(current)
        result: list[str] = []
        for i, chunk in enumerate(chunks):
            if i > 0 and len(chunks[i - 1]) > cls.OVERLAP:
                chunk = chunks[i - 1][-cls.OVERLAP:] + "\n...\n" + chunk
            result.append(chunk)
        return result

    @classmethod
    def _fixed_chunk(cls, text: str) -> list[str]:
        return [text[i:i + cls.CHUNK_SIZE] for i in range(0, len(text), cls.CHUNK_SIZE - cls.OVERLAP)]
