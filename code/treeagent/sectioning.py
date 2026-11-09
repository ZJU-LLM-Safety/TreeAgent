"""Flat/TreeAgent API and JSON adapter; native formats share its planner.

The public surface intentionally contains only the two declared conditions.
Flat slices the compact serialized input into fixed-token sections.
TreeAgent packs complete structural units, searches a tree budget for each example
to approach the Flat section count, emits structural paths, and constructs
child-to-parent residual links using final segment indices.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Iterable, Optional

from .planning import partition_tree, choose_budget


_SAFE_KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
VALID_METHODS = {"flat", "treeagent"}


@dataclass(frozen=True)
class JsonDocuments:
    """An ordered document forest; its virtual root adds no JSON brackets."""
    values: tuple[Any, ...]


def parse_json_text(text: str) -> Any:
    """Read one JSON value or whitespace-separated complete JSON documents."""
    if not isinstance(text, str):
        raise TypeError("JSON source must be text")

    def invalid_constant(value):
        raise ValueError(f"non-finite JSON constant: {value}")

    decoder = json.JSONDecoder(parse_constant=invalid_constant)
    documents = []
    position = 0
    while position < len(text):
        while position < len(text) and text[position] in " \t\r\n":
            position += 1
        if position == len(text):
            break
        value, end = decoder.raw_decode(text, position)
        documents.append(value)
        if end < len(text) and text[end] not in " \t\r\n":
            raise ValueError("complete JSON documents must be separated by whitespace")
        position = end
    if not documents:
        raise ValueError("JSON source must contain at least one document")
    return documents[0] if len(documents) == 1 else JsonDocuments(tuple(documents))


@dataclass
class JsonNode:
    value: Any
    path_parts: tuple[Any, ...]
    parent: Optional["JsonNode"] = None
    key: Optional[str] = None
    index: Optional[int] = None
    children: list["JsonNode"] = field(default_factory=list)
    start: int = 0
    end: int = 0

    @property
    def path(self) -> str:
        return format_path(self.path_parts)

    @property
    def kind(self) -> str:
        if isinstance(self.value, dict):
            return "object"
        if isinstance(self.value, list):
            return "array"
        if isinstance(self.value, str):
            return "string"
        if isinstance(self.value, bool):
            return "boolean"
        if isinstance(self.value, (int, float)) and not isinstance(self.value, bool):
            return "number"
        if self.value is None:
            return "null"
        return type(self.value).__name__

    @property
    def is_leaf(self) -> bool:
        return not self.children


@dataclass
class JsonSection:
    text: str
    raw_text: str
    method: str
    section_type: str
    path: Optional[str] = None
    context_format: str = "json"
    content_text: Optional[str] = None
    content_byte_start: Optional[int] = None
    content_byte_end: Optional[int] = None
    wrapper_prefix: str = ""
    wrapper_suffix: str = ""
    source_byte_start: Optional[int] = None
    source_byte_end: Optional[int] = None
    path_text: str = ""
    path_parts: tuple[Any, ...] = ()
    sibling_range: Optional[tuple[int, int]] = None
    residual_source_indices: list[int] = field(default_factory=list)
    atomic_overflow: bool = False
    candidate_budgets: list[int] = field(default_factory=list)
    unit_path: Optional[str] = None
    parent_path: Optional[str] = None
    ancestor_paths: list[str] = field(default_factory=list)
    scope_parent_paths: dict[str, Optional[str]] = field(default_factory=dict)
    covered_paths: list[str] = field(default_factory=list)
    closing_paths: list[str] = field(default_factory=list)
    content_tokens: int = 0
    total_tokens: int = 0
    path_tokens: int = 0
    wrapper_tokens: int = 0
    step_id: Optional[int] = None
    document_order_index: Optional[int] = None
    traversal_order_index: Optional[int] = None
    traversal_strategy: str = ""
    raw_char_start: Optional[int] = None
    raw_char_end: Optional[int] = None
    raw_token_start: Optional[int] = None
    raw_token_end: Optional[int] = None
    target_flat_sections: Optional[int] = None
    selected_tree_budget: Optional[int] = None
    tree_budget_max: Optional[int] = None
    count_match_exact: Optional[bool] = None
    count_match_delta: Optional[int] = None
    base_section_size: Optional[int] = None

    def render(self) -> str:
        return self.text

    def as_record(self) -> dict[str, Any]:
        record = {
            "method": self.method,
            "context_format": self.context_format,
            "content_text": self.raw_text if self.content_text is None else self.content_text,
            "source_byte_start": self.source_byte_start,
            "source_byte_end": self.source_byte_end,
            "section_type": self.section_type,
            "path": self.path,
            "path_parts": list(self.path_parts),
            "sibling_range": list(self.sibling_range) if self.sibling_range else None,
            "residual_source_indices": self.residual_source_indices,
            "atomic_overflow": self.atomic_overflow,
            "candidate_budgets": self.candidate_budgets,
            "unit_path": self.unit_path,
            "parent_path": self.parent_path,
            "ancestor_paths": self.ancestor_paths,
            "scope_parent_paths": self.scope_parent_paths,
            "covered_paths": self.covered_paths,
            "closing_paths": self.closing_paths,
            "content_tokens": self.content_tokens,
            "total_tokens": self.total_tokens,
            "path_tokens": self.path_tokens,
            "wrapper_tokens": self.wrapper_tokens,
            "step_id": self.step_id,
            "document_order_index": self.document_order_index,
            "traversal_order_index": self.traversal_order_index,
            "traversal_strategy": self.traversal_strategy,
            "raw_char_start": self.raw_char_start,
            "raw_char_end": self.raw_char_end,
            "raw_token_start": self.raw_token_start,
            "raw_token_end": self.raw_token_end,
            "target_flat_sections": self.target_flat_sections,
            "selected_tree_budget": self.selected_tree_budget,
            "tree_budget_max": self.tree_budget_max,
            "count_match_exact": self.count_match_exact,
            "count_match_delta": self.count_match_delta,
            "base_section_size": self.base_section_size,
            "text": self.text,
            "raw_text": self.raw_text,
            "path_text": self.path_text,
        }
        if self.method == "treeagent" and (self.context_format != "json" or self.section_type == "text_span"):
            record.update(
                content_byte_start=self.content_byte_start,
                content_byte_end=self.content_byte_end,
                wrapper_prefix=self.wrapper_prefix,
                wrapper_suffix=self.wrapper_suffix,
            )
        return record


class TokenCounter:
    def __init__(self, tokenizer: Any):
        self.tokenizer = tokenizer
        self._count_cache: dict[str, int] = {}

    def encode(self, text: str) -> list[int]:
        try:
            return self.tokenizer.encode(text, add_special_tokens=False)
        except TypeError:
            return self.tokenizer.encode(text)

    def decode(self, token_ids: Iterable[int]) -> str:
        values = list(token_ids)
        try:
            return self.tokenizer.decode(values, skip_special_tokens=True)
        except TypeError:
            return self.tokenizer.decode(values)

    def count(self, text: str) -> int:
        if text not in self._count_cache:
            self._count_cache[text] = len(self.encode(text))
        return self._count_cache[text]

    def offsets(self, text: str) -> Optional[list[tuple[int, int]]]:
        try:
            encoded = self.tokenizer(
                text,
                add_special_tokens=False,
                return_offsets_mapping=True,
            )
        except Exception:
            return None
        offsets = encoded.get("offset_mapping")
        if offsets is None:
            return None
        return [(int(start), int(end)) for start, end in offsets]


def compact_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def format_path(parts: tuple[Any, ...]) -> str:
    path = "$"
    for part in parts:
        if isinstance(part, int):
            path += f"[{part}]"
        elif _SAFE_KEY_RE.match(part):
            path += f".{part}"
        else:
            path += f"[{json.dumps(part, ensure_ascii=False)}]"
    return path


def build_json_tree(value: Any) -> tuple[JsonNode, str]:
    document_stream = isinstance(value, JsonDocuments)
    if document_stream:
        if not value.values:
            raise ValueError("a document forest must be nonempty")
        value = list(value.values)
    pieces: list[str] = []
    current_pos = 0

    def append(text: str) -> None:
        nonlocal current_pos
        pieces.append(text)
        current_pos += len(text)

    def write(
        node_value: Any,
        path_parts: tuple[Any, ...],
        parent: Optional[JsonNode],
        key: Optional[str],
        index: Optional[int],
        span_start: Optional[int] = None,
    ) -> JsonNode:
        start = current_pos if span_start is None else span_start
        node = JsonNode(node_value, path_parts, parent, key, index)
        node.start = start
        if isinstance(node_value, dict):
            append("{")
            for position, (child_key, child_value) in enumerate(node_value.items()):
                if position:
                    append(",")
                key_start = current_pos
                append(compact_dumps(child_key))
                append(":")
                node.children.append(
                    write(
                        child_value,
                        path_parts + (child_key,),
                        node,
                        child_key,
                        position,
                        key_start,
                    )
                )
            append("}")
        elif isinstance(node_value, list):
            virtual_root = document_stream and parent is None
            if not virtual_root:
                append("[")
            for position, child_value in enumerate(node_value):
                if position:
                    append("\n" if virtual_root else ",")
                node.children.append(
                    write(child_value, path_parts + (position,), node, None, position)
                )
            if not virtual_root:
                append("]")
        else:
            append(compact_dumps(node_value))
        node.end = current_pos
        return node

    root = write(value, (), None, None, None)
    return root, "".join(pieces)


def _char_span(
    offsets: Optional[list[tuple[int, int]]],
    token_start: int,
    token_end: int,
    text_length: int,
    total_tokens: int,
) -> tuple[int, int]:
    if offsets:
        valid = [
            (start, end)
            for start, end in offsets[token_start:token_end]
            if end > start
        ]
        if valid:
            return valid[0][0], valid[-1][1]
    start = int(text_length * token_start / max(total_tokens, 1))
    end = int(text_length * token_end / max(total_tokens, 1))
    return start, max(start + 1, end)


def _scope_info(
    parent: Optional[JsonNode],
) -> tuple[list[str], dict[str, Optional[str]]]:
    nodes: list[JsonNode] = []
    node = parent
    while node is not None:
        nodes.append(node)
        node = node.parent
    nodes.reverse()
    return (
        [node.path for node in nodes],
        {
            node.path: node.parent.path if node.parent is not None else None
            for node in nodes
        },
    )


def flat_sections(
    value: Any, tokenizer: Any, section_size: int
) -> list[JsonSection]:
    if section_size <= 0:
        raise ValueError("section_size must be positive")
    counter = TokenCounter(tokenizer)
    _, context = build_json_tree(value)
    token_ids = counter.encode(context)
    offsets = counter.offsets(context)
    sections = []
    for token_start in range(0, len(token_ids), section_size):
        token_end = min(token_start + section_size, len(token_ids))
        text = counter.decode(token_ids[token_start:token_end])
        char_start, char_end = _char_span(
            offsets, token_start, token_end, len(context), len(token_ids)
        )
        sections.append(
            JsonSection(
                text=text,
                raw_text=text,
                method="flat",
                section_type="linear",
                content_tokens=token_end - token_start,
                total_tokens=counter.count(text),
                raw_char_start=char_start,
                raw_char_end=char_end,
                raw_token_start=token_start,
                raw_token_end=token_end,
            )
        )
    return sections


def _tree_sections_for_budget(
    value: Any, tokenizer: Any, tree_budget: int
) -> list[JsonSection]:
    """Algorithm 1 with JSON string fragments and atomic non-string leaves.

    Subtree content is its compact value serialization. A sibling section is
    a JSON object/list containing its children, including grouping syntax.
    Paths are separate metadata and do not consume the content budget.
    """
    if tree_budget <= 0:
        raise ValueError("tree_budget must be positive")
    counter = TokenCounter(tokenizer)
    root, _ = build_json_tree(value)
    document_stream = isinstance(value, JsonDocuments)

    def node_text(node: JsonNode) -> str:
        if document_stream and node is root:
            return "\n".join(compact_dumps(child.value) for child in node.children)
        return compact_dumps(node.value)

    def group_text(parent: JsonNode, children: list[JsonNode]) -> str:
        if document_stream and parent is root:
            return "\n".join(compact_dumps(child.value) for child in children)
        if len(children) == 1:
            return compact_dumps(children[0].value)
        payload = ({child.key: child.value for child in children}
                   if isinstance(parent.value, dict)
                   else [child.value for child in children])
        return compact_dumps(payload)

    def make_section(
        nodes: list[JsonNode], raw_text: Optional[str] = None,
        fragment: bool = False,
    ) -> JsonSection:
        first = nodes[0]
        parent = first.parent
        grouped = len(nodes) > 1
        if raw_text is None:
            raw_text = (group_text(parent, nodes) if grouped
                        else node_text(first))
        path_parts = parent.path_parts if grouped else first.path_parts
        child_range = (first.index, nodes[-1].index) if grouped else None
        path = format_path(path_parts)
        if grouped:
            # Explicit child positions distinguish a range from an array node.
            path += f"::children[{child_range[0]},{child_range[1]}]"
        path_text = f"<path>\n{path}\n</path>"
        ancestors, parents = _scope_info(parent)
        parents.update({node.path: parent.path if parent else None for node in nodes})
        content_tokens = counter.count(raw_text)
        prefix, suffix = "", ""
        if fragment:
            child = first
            while child.parent is not None:
                if document_stream and child.parent is root:
                    break
                if isinstance(child.parent.value, dict):
                    prefix = "{" + compact_dumps(child.key) + ":" + prefix
                    suffix += "}"
                else:
                    prefix = "[" + prefix
                    suffix += "]"
                child = child.parent
        rendered = prefix + raw_text + suffix
        return JsonSection(
            text=rendered, raw_text=rendered, method="treeagent",
            content_text=raw_text if fragment else None,
            wrapper_prefix=prefix, wrapper_suffix=suffix,
            section_type="text_span" if fragment else "siblings" if grouped else "subtree",
            path=path, path_text=path_text, path_parts=path_parts,
            sibling_range=child_range, unit_path=path,
            parent_path=parent.path if parent else None,
            ancestor_paths=ancestors, scope_parent_paths=parents,
            covered_paths=[node.path for node in nodes],
            content_tokens=content_tokens, path_tokens=counter.count(path_text),
            wrapper_tokens=counter.count(prefix) + counter.count(suffix),
            total_tokens=counter.count(rendered) + counter.count(path_text),
            atomic_overflow=content_tokens > tree_budget,
            raw_char_start=None if fragment else first.start,
            raw_char_end=None if fragment else nodes[-1].end,
        )

    def split_string(node: JsonNode) -> list[JsonSection]:
        # Cut at Unicode code-point boundaries and reserialize each fragment.
        # Every fragment remains valid JSON; escape sequences are never cut.
        # If even one serialized character exceeds B, keep it as an atomic
        # syntax unit, explicitly flagging the overflow.
        fragments: list[JsonSection] = []
        start = 0
        while start < len(node.value):
            end = start + 1
            def safe_end(position):
                if (start < position < len(node.value)
                        and 0xD800 <= ord(node.value[position - 1]) <= 0xDBFF
                        and 0xDC00 <= ord(node.value[position]) <= 0xDFFF):
                    return position - 1
                return position
            if safe_end(end) == start:
                end += 1
            if counter.count(compact_dumps(node.value[start:end])) <= tree_budget:
                # Probe prefixes instead of constructing every prefix of a long
                # leaf. Only a measured fitting prefix can become a fragment;
                # no monotonicity guarantee is needed for budget safety.
                probe = min(len(node.value), start + 2)
                upper = len(node.value)
                while probe > end:
                    boundary = safe_end(probe)
                    if counter.count(compact_dumps(node.value[start:boundary])) > tree_budget:
                        upper = probe - 1
                        break
                    end = boundary
                    if end < probe:
                        probe += 1
                        continue
                    probe = min(len(node.value), start + 2 * (end - start))
                low = end + 1
                while low <= upper:
                    mid = (low + upper) // 2
                    boundary = safe_end(mid)
                    if counter.count(compact_dumps(node.value[start:boundary])) <= tree_budget:
                        end = max(end, boundary)
                        low = mid + 1
                    else:
                        upper = mid - 1
            if end < len(node.value):
                # Prefer the latest whitespace/sentence boundary if its measured
                # serialized content fills at least 80% of B.
                for boundary in range(end, start, -1):
                    if (safe_end(boundary) == boundary
                            and (node.value[boundary - 1].isspace()
                                 or node.value[boundary - 1] in ".!?。！？")
                            and 0.8 * tree_budget <= counter.count(
                                compact_dumps(node.value[start:boundary])) <= tree_budget):
                        end = boundary
                        break
            fragments.append(make_section(
                [node], compact_dumps(node.value[start:end]), fragment=True,
            ))
            start = end
        return fragments or [make_section([node])]

    return partition_tree(
        root, tree_budget,
        count_node=lambda node: counter.count(node_text(node)),
        count_group=lambda parent, children: counter.count(group_text(parent, children)),
        atomic=lambda node: node.is_leaf and not isinstance(node.value, str),
        emit=make_section, split_leaf=split_string,
    )


def count_matched_tree_sections(
    value: Any, tokenizer: Any, section_size: int,
    max_tree_budget: Optional[int] = None,
) -> list[JsonSection]:
    if section_size <= 0:
        raise ValueError("section_size must be positive")
    target = len(flat_sections(value, tokenizer, section_size))
    return choose_budget(
        section_size, max_tree_budget, target,
        lambda budget: _tree_sections_for_budget(value, tokenizer, budget),
    )


def annotate_residual_links(value: Any, sections: list[JsonSection]) -> None:
    """Compute ell(v) and {(ell(v), ell(parent)) : ell(v) < ell(parent)}.

    Segment indices are one-based, matching the manuscript. Actual tree nodes
    include the root and descendants inside intact subtrees. Range labels are
    never treated as nodes. A split leaf closes only on its final fragment.
    """
    root, _ = build_json_tree(value)
    annotate_tree_links(root, sections)


def annotate_tree_links(root, sections: list[JsonSection]) -> None:
    """Shared final-index/link construction for every adapter's original tree."""

    nodes: dict[str, Any] = {}

    def visit(node: Any) -> None:
        nodes[node.path] = node
        for child in node.children:
            visit(child)
    visit(root)
    final: dict[str, int] = {}

    def cover(node: Any, step: int) -> None:
        final[node.path] = step
        for child in node.children:
            cover(child, step)

    for step, section in enumerate(sections, start=1):
        for path in section.covered_paths:
            node = nodes[path]
            cover(node, step)
            parent = node.parent
            while parent is not None:
                final[parent.path] = step
                parent = parent.parent
    if set(final) != set(nodes):
        raise ValueError("sections must cover the complete input tree")
    incoming: dict[int, set[int]] = {}
    for node in nodes.values():
        if node.parent is not None:
            source, target = final[node.path], final[node.parent.path]
            if source < target:
                incoming.setdefault(target, set()).add(source)
    closes: dict[int, list[str]] = {}
    for path, step in final.items():
        closes.setdefault(step, []).append(path)
    for step, section in enumerate(sections, start=1):
        section.step_id = step
        section.document_order_index = step - 1
        section.traversal_order_index = step - 1
        section.traversal_strategy = "left_to_right_dfs"
        section.closing_paths = closes.get(step, [])
        section.residual_source_indices = sorted(incoming.get(step, set()))
        section.scope_parent_paths.update({
            path: nodes[path].parent.path if nodes[path].parent else None
            for path in section.closing_paths
        })


def build_sections(
    value: Any, tokenizer: Any, section_size: int, method: str, *,
    max_tree_budget: Optional[int] = None, max_sections: int = 0,
    context_format: str = "json",
) -> list[JsonSection]:
    if method not in VALID_METHODS:
        raise ValueError(f"unknown method {method!r}; expected one of {sorted(VALID_METHODS)}")
    if max_sections:
        raise ValueError("partial plans are unsupported: residual links require the full tree")
    if context_format != "json":
        from .native_source import build_source_sections
        return build_source_sections(value, context_format, tokenizer, section_size,
                                     method, max_tree_budget=max_tree_budget)
    if method == "flat":
        sections = flat_sections(value, tokenizer, section_size)
        for step, section in enumerate(sections, start=1):
            section.step_id = step
        return sections
    sections = count_matched_tree_sections(value, tokenizer, section_size, max_tree_budget)
    annotate_residual_links(value, sections)
    return sections


def section_stats(sections: list[JsonSection]) -> dict[str, Any]:
    stats: dict[str, Any] = {
        "num_sections": len(sections),
        "content_tokens": sum(section.content_tokens for section in sections),
        "total_tokens": sum(section.total_tokens for section in sections),
        "path_token_overhead": sum(section.path_tokens for section in sections),
        "wrapper_token_overhead": sum(
            section.wrapper_tokens for section in sections
        ),
        "closing_scope_events": sum(
            len(section.closing_paths) for section in sections
        ),
    }
    if sections and sections[0].selected_tree_budget is not None:
        first = sections[0]
        stats.update(
            {
                "target_flat_sections": first.target_flat_sections,
                "actual_tree_sections": len(sections),
                "selected_tree_budget": first.selected_tree_budget,
                "tree_budget_max": first.tree_budget_max,
                "count_match_exact": first.count_match_exact,
                "count_match_delta": first.count_match_delta,
                "base_section_size": first.base_section_size,
            }
        )
    return stats
