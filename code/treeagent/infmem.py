"""Shared raw-input retrieval corpus for Flat and TreeAgent host integrations.

Build retrieval documents for the host BM25 index from the original raw input.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .sectioning import TokenCounter


@dataclass(frozen=True)
class InfMemRetrievalChunk:
    text: str
    raw_window_index: int
    token_start: int
    token_end: int


def build_infmem_retrieval_corpus(
    raw_text: str, tokenizer: Any, *, raw_window_tokens: int = 5000,
) -> list[InfMemRetrievalChunk]:
    """Build the same 500-token corpus for both methods from identical raw text.

    The existing Flat corpus uses 100-token overlap within canonical raw
    recurrent windows. Windows stay independent of TreeAgent's sections.
    Token offsets are zero-based and end-exclusive. Short terminal chunks
    stop at each raw window boundary. Pass original text, including JSON
    whitespace, rather than serialized structural sections.
    """
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be the original input string")
    if isinstance(raw_window_tokens, bool) or not isinstance(raw_window_tokens, int) or raw_window_tokens <= 0:
        raise ValueError("raw_window_tokens must be a positive integer")
    counter = TokenCounter(tokenizer)
    tokens = counter.encode(raw_text)
    chunks = []
    for window_index, window_start in enumerate(range(0, len(tokens), raw_window_tokens)):
        window_end = min(len(tokens), window_start + raw_window_tokens)
        start = window_start
        while start < window_end:
            end = min(window_end, start + 500)
            chunks.append(InfMemRetrievalChunk(
                counter.decode(tokens[start:end]), window_index, start, end,
            ))
            if end == window_end:
                break
            start += 400
    return chunks
