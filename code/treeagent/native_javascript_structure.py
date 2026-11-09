"""JavaScript semantic units backed by original UTF-8 source intervals.

Only native statement/member/property/element boundaries become children.
Expression syntax is traversed to find these containers, never emitted as
identifier, keyword, operator, quote or punctuation units. No code is executed.
"""
from __future__ import annotations

from .native_tree import SpanNode, _parser


_CONTAINERS = {"program", "statement_block", "class_body", "object", "array"}
_ATOMIC = {"string", "template_string", "regex", "comment"}


def parse_native_javascript(raw_text: str) -> SpanNode:
    """Return complete native units with local (not cumulative) lexical shells."""
    raw = raw_text.encode("utf-8")
    syntax = _parser("javascript").parse(raw).root_node
    if syntax.has_error:
        raise ValueError("malformed javascript source")

    def text(start, end):
        return raw[start:end].decode("utf-8")

    def frontier(syntax_node):
        # Stop at each native container. Strings (including interpolated
        # templates) remain lexical leaves; the common overflow splitter owns
        # their continuation rather than exposing quotes/escapes as children.
        if syntax_node.type in _CONTAINERS:
            return [syntax_node]
        if syntax_node.type in {"lexical_declaration", "variable_declaration"} and sum(
            child.type == "variable_declarator" for child in syntax_node.named_children
        ) > 1:
            # Preserve the binding frontier through wrappers such as export.
            return [syntax_node]
        if syntax_node.type in _ATOMIC:
            return []
        found = []
        for child in syntax_node.named_children:
            found.extend(frontier(child))
        return found

    def populate(logical, syntax_node):
        containers = frontier(syntax_node)
        declarators = [c for c in syntax_node.named_children
                       if c.type == "variable_declarator"]
        if syntax_node.type in {"lexical_declaration", "variable_declaration"} and len(declarators) > 1:
            # A declaration list owns complete name=value bindings. Jumping
            # directly to initializer containers would attach later values to
            # the first binding's repeated lexical shell.
            candidates = list(syntax_node.named_children)
        elif len(containers) == 1:
            # Absorb the expression/declaration/property shell. Descendants
            # receive e.g. `const config={` or `enabled:[` as context, while
            # the raw intervals remain the unmodified complete native units.
            container = containers[0]
            if container.type == "array":
                previous = "["
                for child in container.children[1:]:
                    if child.type == "comment":
                        continue
                    if child.type == "," and previous in {"[", ","}:
                        # Elisions carry array indices despite having no named
                        # CST child. A partial envelope must not erase holes.
                        logical.atomic = True
                        return
                    previous = child.type
            candidates = list(container.named_children)
        elif containers:
            # A shared shell cannot retain positions/operators between multiple
            # argument, branch, or operand containers. Keep the expression whole
            # instead of presenting its later container as the first argument.
            logical.atomic = True
            return
        else:
            # Opaque syntax (calls, regex, comments, operators) has no proven
            # fragment rendering. Only literal text opts into continuation.
            logical.atomic = True
            value = syntax_node
            while True:
                if value.type in {"pair", "variable_declarator"}:
                    child = value.child_by_field_name("value")
                elif value.type in {"lexical_declaration", "variable_declaration",
                                     "export_statement", "parenthesized_expression",
                                     "expression_statement", "return_statement"}:
                    named = [c for c in value.named_children if c.type != "comment"]
                    child = named[0] if len(named) == 1 else None
                else:
                    child = None
                if child is None:
                    break
                value = child
            if value.type in {"string", "template_string"}:
                # Keep the binding and original quotes around overflow spans.
                # Escape-aware cuts themselves belong to the shared planner.
                logical.context_prefix = text(logical.start, value.start_byte + 1)
                logical.context_suffix = text(value.end_byte - 1, logical.end)
                logical.kind = value.type
                logical.atomic = False
                if value.type == "template_string" and any(
                    child.type == "template_substitution" for child in value.named_children
                ):
                    logical.atomic = True
            return
        counts = {}
        for child in candidates:
            counts[child.type] = counts.get(child.type, 0) + 1
            path = f"{logical.path.rstrip('/')}/{child.type}[{counts[child.type]}]"
            node = SpanNode(child.type, child.start_byte, child.end_byte,
                            path=path, parent=logical)
            logical.children.append(node)
            populate(node, child)
        if logical.children:
            logical.context_prefix = text(logical.start, logical.children[0].start)
            logical.context_suffix = text(logical.children[-1].end, logical.end)

    root = SpanNode("program", 0, len(raw), path="/")
    populate(root, syntax)
    return root
