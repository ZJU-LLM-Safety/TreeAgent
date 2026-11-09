"""Source-located native trees; parser dependencies are loaded on demand."""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
import re


@dataclass
class SpanNode:
    kind: str
    start: int
    end: int
    path: str = ""
    parent: "SpanNode | None" = None
    children: list["SpanNode"] = field(default_factory=list)
    context_prefix: str = ""
    context_suffix: str = ""
    atomic: bool = False


@lru_cache(maxsize=None)
def _parser(context_format):
    try:
        from tree_sitter_languages import get_parser
        return get_parser(context_format)
    except (ImportError, TypeError) as exc:
        raise RuntimeError(
            "Native formats require the compatible parser versions in requirements.txt"
        ) from exc


def parse_native_tree(text, context_format):
    from importlib import import_module
    if context_format not in {"html", "yaml", "javascript"}:
        raise ValueError(f"unsupported native format: {context_format}")
    module = import_module(f".native_{context_format}_structure", __package__)
    parse = getattr(module, f"parse_native_{context_format}")
    if context_format != "javascript":
        return parse(text)
    # Recognize file boundaries only in top-level comment nodes, never inside
    # strings or templates. Each marked source keeps its own native hierarchy.
    raw = text.encode("utf-8")
    syntax = _parser("javascript").parse(raw).root_node
    if syntax.has_error:
        raise ValueError("malformed javascript source")
    pattern = re.compile(rb'// @structured-javascript-(?:source|state|file)\s+\{[^\n]*\}\s*$')
    markers = [c.start_byte for c in syntax.named_children
               if c.type == "comment" and pattern.fullmatch(raw[c.start_byte:c.end_byte])]
    if not markers:
        return parse(text)
    root = SpanNode("source_forest", 0, len(raw), path="/")
    starts = [0, *markers[1:]]
    for index, start in enumerate(starts):
        end = starts[index + 1] if index + 1 < len(starts) else len(raw)
        child = parse(raw[start:end].decode("utf-8"))
        old_root_path = child.path
        prefix = f"/source[{index}]"
        def rebase(node):
            node.start += start
            node.end += start
            node.path = prefix + node.path[len(old_root_path):]
            # A nonroot path retains a separator after the source prefix.
            if node is not child:
                node.path = prefix + "/" + node.path[len(prefix):].lstrip("/")
            for descendant in node.children:
                rebase(descendant)
        rebase(child)
        child.parent = root
        root.children.append(child)
    return root
