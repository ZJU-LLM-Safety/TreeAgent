"""Query-guided retrieval over child-to-parent linked segment memories."""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from .sectioning import JsonSection, TokenCounter

POLICY = "child_to_parent_final_segment"

_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
    "has", "have", "in", "is", "it", "its", "of", "on", "or", "that",
    "the", "this", "to", "was", "were", "what", "when", "where", "which",
    "who", "with",
}


def terms(text: str) -> list[str]:
    expanded = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", str(text))
    raw_terms = re.findall(r"[A-Za-z0-9_.$/-]+", expanded.lower())
    output: list[str] = []
    for term in raw_terms:
        for part in re.split(r"[_\s]+", term):
            part = part.strip(".-/")
            if len(part) >= 2 and part not in _STOPWORDS:
                output.append(part)
    return output


def split_memory(text: str) -> list[str]:
    spans: list[str] = []
    for line in re.split(r"[\r\n]+", str(text or "").strip()):
        line = re.sub(r"^\s*[-*+]\s+", "", line).strip()
        if line:
            spans.extend(
                part.strip()
                for part in re.split(r"(?<=[.!?。！？])\s+", line)
                if part.strip()
            )
    return spans


def clip_tokens(tokenizer: Any, text: str, max_tokens: int) -> str:
    counter = TokenCounter(tokenizer)
    token_ids = counter.encode(text)
    return counter.decode(token_ids[:max_tokens]).strip()


@dataclass(frozen=True)
class Candidate:
    source_index: int
    span_index: int
    text: str
    score: float


@dataclass
class ResidualMemoryStore:
    tokenizer: Any
    top_k: int = 4
    item_max_tokens: int = 96
    memory_by_index: dict[int, str] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        if self.top_k < 0 or self.item_max_tokens <= 0:
            raise ValueError("top_k must be nonnegative and item_max_tokens positive")

    def record(self, section: JsonSection, memory: str) -> None:
        # Every segment is saved, including fragments that close no node.
        if section.step_id != len(self.memory_by_index) + 1:
            raise ValueError("save each segment once, in order, after its update")
        if not isinstance(memory, str):
            raise TypeError("memory must be a text state")
        self.memory_by_index[section.step_id] = memory

    def render(self, section: JsonSection, question: str) -> tuple[str, dict[str, Any]]:
        target = section.step_id
        if target != len(self.memory_by_index) + 1:
            raise ValueError("retrieve before updating the next segment")
        sources = sorted(set(section.residual_source_indices))
        if any(source >= target or source not in self.memory_by_index for source in sources):
            raise ValueError("residual sources must be saved, strictly earlier segment indices")
        stats = {"residual_policy": POLICY, "residual_added": False,
                 "residual_linked_indices": sources, "residual_source_indices": [],
                 "residual_candidate_spans": 0, "residual_item_count": 0,
                 "residual_tokens": 0}
        query_terms = Counter(terms(question))
        candidates: list[Candidate] = []
        for source in sources:
            for span_index, span in enumerate(split_memory(self.memory_by_index[source])):
                # Score the complete span, without paths/indices; truncate only
                # after selection, following the manuscript's operation order.
                span_terms = Counter(terms(span))
                overlap = set(query_terms) & set(span_terms)
                score = sum(min(query_terms[t], span_terms[t]) for t in overlap)
                score += 0.25 * len(overlap)
                if score > 0:
                    candidates.append(Candidate(source, span_index, span, score))
        candidates.sort(key=lambda item: (-item.score, item.source_index, item.span_index))
        stats["residual_candidate_spans"] = len(candidates)
        selected = candidates[:self.top_k]
        clipped = [(candidate, clip_tokens(self.tokenizer, candidate.text, self.item_max_tokens))
                   for candidate in selected]
        clipped = [(candidate, text) for candidate, text in clipped if text]
        residual = "\n".join(text for _, text in clipped)
        stats.update({
            "residual_added": bool(residual),
            "residual_source_indices": [candidate.source_index for candidate, _ in clipped],
            "residual_item_count": len(clipped),
            "residual_tokens": len(TokenCounter(self.tokenizer).encode(residual)),
        })
        return residual, stats
