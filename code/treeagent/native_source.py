"""Native HTML/YAML/JavaScript adapters for the shared TreeAgent planner."""
from __future__ import annotations

import re
from typing import Any

from .native_tree import parse_native_tree
from .planning import choose_budget, partition_tree
from .sectioning import JsonSection, TokenCounter, annotate_tree_links


def walk(node):
    yield node
    for child in node.children:
        yield from walk(child)


def validate_tree(root, raw):
    paths = set()
    if (root.start, root.end) != (0, len(raw)):
        raise ValueError('native tree must cover the complete source')
    for node in walk(root):
        if node.path in paths:
            raise ValueError('native tree paths must be unique')
        paths.add(node.path)
        if not 0 <= node.start <= node.end <= len(raw):
            raise ValueError('invalid native source interval')
        raw[node.start:node.end].decode('utf-8')
        previous = node.start
        for child in node.children:
            if child.parent is not node or not previous <= child.start <= child.end <= node.end:
                raise ValueError('native children must be ordered, disjoint, and inside their parent')
            previous = child.end


def chain(node):
    result = []
    while node is not None:
        result.append(node)
        node = node.parent
    return list(reversed(result))


def path_parts(node):
    return tuple(child.path[len(child.parent.path):].lstrip('/')
                 for child in chain(node) if child.parent is not None)


def source_layout(root):
    """Locate source wrappers without changing original subtree intervals.

    These envelopes are used only when rendering a selected section. Budget
    decisions always use the original parser's subtree or sibling spans.
    """
    intervals = {}
    def assign(node, start, end):
        intervals[node.path] = (start, end)
        cursor = start
        for i, child in enumerate(node.children):
            stop = child.end if i + 1 < len(node.children) else end
            assign(child, cursor, stop)
            cursor = stop
    assign(root, root.start, root.end)
    return intervals


def safe_ends(text, node, context_format):
    """Character ends that preserve an escape/entity and lexical opening/close."""
    start = len(node.context_prefix)
    end = len(text) - len(node.context_suffix)
    if start >= end:
        return [len(text)]
    safe = set(range(start + 1, end + 1))
    if context_format == 'javascript':
        # Escaped UTF-16 surrogate pairs form one atom. Keep all other escaped
        # units, escaped newlines, code-point escapes, and quotes uncut as well.
        pattern = re.compile(r'\\u[Dd][89AaBb][0-9a-fA-F]{2}\\u[Dd][CcDdEeFf][0-9a-fA-F]{2}'
                             r'|\\(?:u\{[0-9a-fA-F]+\}|u[0-9a-fA-F]{4}|x[0-9a-fA-F]{2}|\r\n|[\s\S])')
        for match in pattern.finditer(text, start, end):
            safe.difference_update(range(match.start() + 1, match.end()))
    if context_format == 'html':
        for match in re.finditer(r'&(?:#[xX][0-9a-fA-F]+|#[0-9]+|[A-Za-z][A-Za-z0-9]*);', text):
            safe.difference_update(range(match.start() + 1, match.end()))
    # The original closing syntax stays attached to the last payload atom;
    # never emit a standalone quote, semicolon, or other closing envelope.
    if node.context_suffix and end in safe:
        safe.remove(end)
    safe.add(len(text))
    return sorted(safe)


def source_sections_for_budget(text, context_format, tokenizer, budget, root=None, layout=None):
    raw = text.encode('utf-8')
    root = root or parse_native_tree(text, context_format)
    validate_tree(root, raw)
    layout = source_layout(root) if layout is None else layout
    counter = TokenCounter(tokenizer)

    def source(start, end):
        return raw[start:end].decode('utf-8')

    def emit(nodes, span=None):
        first, last = nodes[0], nodes[-1]
        grouped = len(nodes) > 1
        parent = first.parent
        owner = parent if grouped else first
        position = {id(child): i for i, child in enumerate(parent.children)} if parent else {}
        interval = (position[id(first)], position[id(last)]) if grouped else None
        path = owner.path
        if grouped:
            path += f'::children[{interval[0]},{interval[1]}]'
        start, end = span if span is not None else (first.start, last.end)
        content = source(start, end)
        raw_start = layout[first.path][0] if start == first.start else start
        raw_end = layout[last.path][1] if end == last.end else end
        prefix, suffix = source(raw_start, start), source(end, raw_end)
        rendered = prefix + content + suffix
        ancestors = chain(parent)
        path_text = f'<path>\n{path}\n</path>'
        return JsonSection(
            text=rendered, raw_text=rendered, content_text=content,
            wrapper_prefix=prefix, wrapper_suffix=suffix,
            content_byte_start=start, content_byte_end=end,
            context_format=context_format, method='treeagent',
            section_type='text_span' if span is not None else 'siblings' if grouped else 'subtree',
            path=path, path_text=path_text, path_parts=path_parts(owner), sibling_range=interval,
            unit_path=path, parent_path=parent.path if parent else None,
            ancestor_paths=[n.path for n in ancestors],
            scope_parent_paths={n.path: n.parent.path if n.parent else None for n in [*ancestors, *nodes]},
            covered_paths=[n.path for n in nodes],
            content_tokens=counter.count(content), path_tokens=counter.count(path_text),
            wrapper_tokens=counter.count(prefix) + counter.count(suffix),
            total_tokens=counter.count(rendered) + counter.count(path_text),
            atomic_overflow=counter.count(content) > budget,
            source_byte_start=raw_start, source_byte_end=raw_end,
        )

    def split_leaf(node):
        value = source(node.start, node.end)
        boundaries = safe_ends(value, node, context_format)
        # Translate whole Unicode characters to byte offsets once. Source text
        # is never decoded from a partial model-token sequence.
        offsets = [0]
        for char in value:
            offsets.append(offsets[-1] + len(char.encode('utf-8')))
        sections = []
        start, first = 0, 0
        while start < len(value):
            best = first
            if counter.count(value[start:boundaries[best]]) <= budget:
                probe = min(len(boundaries) - 1, first + 1)
                upper = len(boundaries) - 1
                while probe > best:
                    if counter.count(value[start:boundaries[probe]]) > budget:
                        upper = probe - 1
                        break
                    best = probe
                    probe = min(len(boundaries) - 1, first + 2 * (best - first + 1))
                low = best + 1
                while low <= upper:
                    mid = (low + upper) // 2
                    if counter.count(value[start:boundaries[mid]]) <= budget:
                        best = mid
                        low = mid + 1
                    else:
                        upper = mid - 1
            stop = boundaries[best]
            sections.append(emit([node], (node.start + offsets[start], node.start + offsets[stop])))
            start, first = stop, best + 1
        return sections or [emit([node])]

    sections = partition_tree(
        root, budget,
        count_node=lambda n: counter.count(source(n.start, n.end)),
        count_group=lambda parent, nodes: counter.count(source(nodes[0].start, nodes[-1].end)),
        atomic=lambda node: node.atomic,
        emit=emit, split_leaf=split_leaf,
    )
    annotate_tree_links(root, sections)
    if ''.join(s.raw_text for s in sections) != text:
        raise ValueError('section plan must preserve every source byte exactly once')
    return sections


def build_source_sections(text: str, context_format: str, tokenizer: Any, section_size: int,
                          method: str, *, max_tree_budget=None):
    if context_format not in {'html', 'yaml', 'javascript'}:
        raise ValueError(f'unsupported context_format: {context_format}')
    if not isinstance(text, str):
        raise TypeError('native-format input must be source text')
    if section_size <= 0:
        raise ValueError('section_size must be positive')
    if method not in {'flat', 'treeagent'}:
        raise ValueError(f'unknown method: {method}')
    counter = TokenCounter(tokenizer)
    ids = counter.encode(text)
    target = (len(ids) + section_size - 1) // section_size
    if method == 'flat':
        return [JsonSection(
            text=counter.decode(ids[start:start + section_size]),
            raw_text=counter.decode(ids[start:start + section_size]),
            context_format=context_format, method='flat', section_type='linear',
            step_id=i + 1, content_tokens=len(ids[start:start + section_size]),
            total_tokens=len(ids[start:start + section_size]),
            raw_token_start=start, raw_token_end=min(start + section_size, len(ids)),
        ) for i, start in enumerate(range(0, len(ids), section_size))]
    if not text:
        return choose_budget(section_size, max_tree_budget, 0, lambda budget: [], native=True)
    root = parse_native_tree(text, context_format)
    layout = source_layout(root)
    return choose_budget(section_size, max_tree_budget, target,
                         lambda budget: source_sections_for_budget(text, context_format, tokenizer, budget, root, layout),
                         native=True)
