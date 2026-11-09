"""TreeAgent sectioning, memory links, and retrieval."""
from .residual import ResidualMemoryStore
from .runtime import AgentResult, Observation, run_memory_agent
from .sectioning import JsonSection, build_sections, section_stats, parse_json_text
from .infmem import InfMemRetrievalChunk, build_infmem_retrieval_corpus

Section = JsonSection

__all__ = ["Section", "JsonSection", "ResidualMemoryStore", "Observation", "AgentResult",
           "build_sections", "section_stats", "run_memory_agent", "parse_json_text",
           "InfMemRetrievalChunk", "build_infmem_retrieval_corpus"]
