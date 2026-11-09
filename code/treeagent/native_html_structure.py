"""Source-located HTML elements, without tag/attribute grammar scaffolding.

The parser supplies byte locations, never serialized markup.  Missing optional
end tags stay missing; uncertain syntax is an opaque source leaf.  Envelopes
are the node's own original tags, for the shared planner's ancestor context.
"""

from __future__ import annotations

from .native_tree import SpanNode, _parser

_ELEMENT_KINDS = frozenset({"element", "script_element", "style_element"})
_TAG_KINDS = frozenset({"start_tag", "end_tag", "self_closing_tag"})
_VOID_NAMES = frozenset({
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link",
    "meta", "param", "source", "track", "wbr",
})
# Some tree-sitter HTML versions miss these optional end-tag transitions.
# This is a source-tree correction, not DOM insertion or serialization: only
# an element without its own end tag can end at the next sibling's opening.
_OPTIONAL_END_TRIGGERS = {
    "li": {"li"},
    "dt": {"dt", "dd"}, "dd": {"dt", "dd"},
    "rt": {"rt", "rp"}, "rp": {"rt", "rp"},
    "option": {"option", "optgroup"}, "optgroup": {"optgroup"},
    "thead": {"tbody", "tfoot"}, "tbody": {"tbody", "tfoot"},
    "tr": {"tr", "thead", "tbody", "tfoot"},
    "th": {"th", "td", "tr", "thead", "tbody", "tfoot"},
    "td": {"th", "td", "tr", "thead", "tbody", "tfoot"},
}


def parse_native_html(raw_text: str) -> SpanNode:
    """Return ordered native element/text spans over the complete UTF-8 input.

    HTML permits omitted end tags and fragments, so tree-sitter recovery does
    not alone reject a document. Error spans remain opaque instead of treating
    recovered attribute/tag grammar as a trustworthy semantic hierarchy.
    """
    raw = raw_text.encode("utf-8")
    parsed = _parser("html").parse(raw).root_node
    root = SpanNode("source", 0, len(raw), path="/")

    def lexeme(start: int, end: int) -> str:
        return raw[start:end].decode("utf-8", errors="strict")

    def convert(ts_node) -> list[SpanNode]:
        if ts_node.end_byte <= ts_node.start_byte:
            return []
        kind = str(ts_node.type)
        if kind not in _ELEMENT_KINDS:
            # In particular, comments and script raw text are indivisible
            # grammar leaves even if the parser exposes internal children.
            return [SpanNode(kind, ts_node.start_byte, ts_node.end_byte,
                             atomic=kind != "text")]
        opening = next((c for c in ts_node.named_children
                        if c.type in {"start_tag", "self_closing_tag"}), None)
        if opening is None:
            return [SpanNode("element", ts_node.start_byte, ts_node.end_byte)]
        tag = next((c for c in opening.named_children if c.type == "tag_name"), None)
        name = lexeme(tag.start_byte, tag.end_byte).lower() if tag else "element"
        node = SpanNode(name, ts_node.start_byte, ts_node.end_byte)
        node.context_prefix = lexeme(opening.start_byte, opening.end_byte)
        closing = next((c for c in reversed(ts_node.named_children)
                        if c.type == "end_tag" and not c.is_missing), None)
        node.context_suffix = (lexeme(closing.start_byte, closing.end_byte)
                               if closing is not None else "")
        content = [c for c in ts_node.named_children if c.type not in _TAG_KINDS]
        children = [child for c in content for child in convert(c)]
        if name in _VOID_NAMES or opening.type == "self_closing_tag":
            # Some grammar versions attach following text to <br>. Native HTML
            # void elements end at their opening tag; promote that content.
            node.end = opening.end_byte
            node.context_suffix = ""
            siblings = [c for c in children if c.start >= node.end]
            if closing is not None:
                siblings.append(SpanNode("erroneous_end_tag", closing.start_byte,
                                         closing.end_byte))
            return [node, *sorted(siblings, key=lambda c: c.start)]
        node.children = children
        return [node]

    root.children = [child for c in parsed.named_children for child in convert(c)]

    def close_optional(node: SpanNode) -> list[SpanNode]:
        node.children = [part for child in node.children
                         for part in close_optional(child)]
        if not node.context_suffix:
            triggers = _OPTIONAL_END_TRIGGERS.get(node.kind, ())
            for index, child in enumerate(node.children):
                if child.kind in triggers:
                    promoted = node.children[index:]
                    node.children = node.children[:index]
                    node.end = child.start
                    return [node, *promoted]
        return [node]

    close_optional(root)

    def bind(node: SpanNode) -> None:
        counts: dict[str, int] = {}
        previous = node.start
        for child in node.children:
            if not (previous <= child.start < child.end <= node.end):
                raise ValueError("HTML parser produced overlapping native spans")
            previous = child.end
            counts[child.kind] = counts.get(child.kind, 0) + 1
            child.parent = node
            child.path = f"{node.path.rstrip('/')}/{child.kind}[{counts[child.kind]}]"
            bind(child)

    bind(root)
    return root
