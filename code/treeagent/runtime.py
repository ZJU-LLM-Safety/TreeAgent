"""Controller-neutral implementation of the manuscript's update ordering.

Callbacks retain the host agent's own update, auxiliary context, and answer
procedures.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .residual import ResidualMemoryStore
from .sectioning import JsonSection


@dataclass(frozen=True)
class Observation:
    section: JsonSection
    structural_path: str
    residual: str
    native_context: Any


@dataclass
class AgentResult:
    answer: Any
    memory: str
    history: dict[int, str]
    retrieval: list[dict[str, Any]]


def run_memory_agent(
    sections: list[JsonSection], question: str, tokenizer: Any,
    update: Callable[[str, str, Observation], str],
    answer: Callable[[str, str], Any], *,
    native_context: Callable[[JsonSection, str], Any] | None = None,
    top_k: int = 4, item_max_tokens: int = 96,
) -> AgentResult:
    store = ResidualMemoryStore(tokenizer, top_k, item_max_tokens)
    memory = ""
    retrieval = []
    for section in sections:
        residual, stats = store.render(section, question)
        context = native_context(section, memory) if native_context else None
        observation = Observation(section, section.path_text, residual, context)
        memory = update(question, memory, observation)
        store.record(section, memory)
        retrieval.append(stats)
    return AgentResult(answer(question, memory), memory, dict(store.memory_by_index), retrieval)
