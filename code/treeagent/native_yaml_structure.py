"""Native YAML entry/item hierarchy carried by untouched UTF-8 spans.

Aliases and tags remain source lexemes: this adapter never resolves a reference
or interprets application schemas. Paths identify lexical keys (including their
quoting) and distinguish repeated keys without changing the source.
"""
from __future__ import annotations

import json

from .native_tree import SpanNode, _parser


_MAPPINGS = {"block_mapping", "flow_mapping"}
_SEQUENCES = {"block_sequence", "flow_sequence"}
_CONTAINERS = _MAPPINGS | _SEQUENCES
_WRAPPERS = {"block_node", "flow_node", "document"}


def parse_native_yaml(raw_text: str) -> SpanNode:
    """Build complete mapping entries and sequence items, not CST wrappers."""
    raw = raw_text.encode("utf-8")
    syntax = _parser("yaml").parse(raw).root_node
    if syntax.has_error:
        raise ValueError("malformed yaml source")

    def text(start: int, end: int) -> str:
        return raw[start:end].decode("utf-8")

    def unwrap(node):
        while node is not None and node.type in _WRAPPERS:
            children = [c for c in node.named_children
                        if c.type not in {"comment", "anchor", "tag", "yaml_directive", "tag_directive"}]
            if len(children) != 1:
                break
            node = children[0]
        return node

    def scalar_atomic(payload, original):
        # Only unadorned plain string text has the continuation contract.
        # Quotes, tags, anchors, aliases and typed scalars carry semantics that
        # would change if a continuation were rendered as a fresh plain value.
        if payload.type != "plain_scalar" or any(
            child.type != "string_scalar" for child in payload.named_children
        ):
            return True
        while original is not None and original.type in _WRAPPERS:
            if any(c.type in {"anchor", "tag"} for c in original.named_children):
                return True
            children = [c for c in original.named_children if c.type not in {
                "comment", "yaml_directive", "tag_directive"}]
            if len(children) != 1:
                break
            original = children[0]
        return False

    def shell(node: SpanNode, content_start: int, content_end: int) -> None:
        # These are this node's own shell only. The planner composes ancestors.
        node.context_prefix = text(node.start, content_start)
        suffix = text(content_end, node.end)
        # Whitespace after another sibling is not a lexical closing delimiter.
        # Repeating it after a keep-chomp scalar changes that scalar's value.
        node.context_suffix = suffix if suffix.strip() else ""

    def fill(node: SpanNode, container) -> None:
        mapping = container.type in _MAPPINGS
        children = [c for c in container.named_children if c.type != "comment"]
        seen: dict[str, int] = {}
        for index, child in enumerate(children):
            if mapping:
                key = child.child_by_field_name("key")
                label = text(key.start_byte, key.end_byte) if key is not None else ""
                seen[label] = seen.get(label, 0) + 1
                path = node.path + "[" + json.dumps(label, ensure_ascii=False) + "]"
                if seen[label] > 1:
                    path += f"#occurrence[{seen[label]}]"
                value = child.child_by_field_name("value")
                kind = "yaml_mapping_entry"
            else:
                path = f"{node.path}[{index}]"
                value = child
                if child.type == "block_sequence_item":
                    value = next((c for c in child.named_children if c.type != "comment"), None)
                kind = "yaml_sequence_item"
            logical = SpanNode(kind, child.start_byte, child.end_byte, path=path, parent=node)
            node.children.append(logical)
            payload = unwrap(value)
            if payload is not None and payload.type in _CONTAINERS:
                fill(logical, payload)
            elif payload is not None:
                # A scalar is indivisible structurally, even when tree-sitter
                # has string/escape children. Only plain text may continue.
                logical.kind = "yaml_" + payload.type
                logical.atomic = scalar_atomic(payload, value)
                shell(logical, payload.start_byte, payload.end_byte)
                if payload.type == "block_scalar":
                    # Header, indentation, folding and chomping form one value.
                    # CST spans exclude trailing line breaks, but those bytes
                    # belong to the scalar (especially with keep chomping).
                    logical.atomic = True
                    tail = logical.end
                    last_line_end = tail
                    while tail < len(raw) and raw[tail] in b" \t\r\n":
                        tail += 1
                        if raw[tail - 1] == 10:
                            last_line_end = tail
                    logical.end = last_line_end
            else:
                logical.context_prefix = ""
                logical.context_suffix = ""
        if node.children:
            node.end = max(node.end, node.children[-1].end)
            shell(node, node.children[0].start, node.children[-1].end)
        else:
            node.context_prefix = ""
            node.context_suffix = ""

    documents = [c for c in syntax.named_children if c.type == "document"]
    root = SpanNode("yaml_source", 0, len(raw), path="$")
    root.context_prefix = ""
    root.context_suffix = ""
    if len(documents) == 1:
        content = unwrap(documents[0])
        if content.type in _CONTAINERS:
            root.kind = "yaml_mapping" if content.type in _MAPPINGS else "yaml_sequence"
            fill(root, content)
        else:
            root.kind = "yaml_" + content.type
            root.atomic = scalar_atomic(content, documents[0])
        return root
    for index, document in enumerate(documents):
        node = SpanNode("yaml_document", document.start_byte, document.end_byte,
                        path=f"$document[{index}]", parent=root)
        node.context_prefix = ""
        node.context_suffix = ""
        root.children.append(node)
        content = unwrap(document)
        if content.type in _CONTAINERS:
            node.kind = "yaml_mapping" if content.type in _MAPPINGS else "yaml_sequence"
            fill(node, content)
        else:
            node.kind = "yaml_" + content.type
            node.atomic = scalar_atomic(content, document)
    return root
