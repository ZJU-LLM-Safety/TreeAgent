"""Format-independent partitioning and candidate-budget selection."""
from __future__ import annotations


def partition_tree(root, budget, *, count_node, count_group, atomic, emit, split_leaf):
    """Algorithm 1; adapters supply serialization and permitted leaf boundaries."""
    def partition(node):
        if count_node(node) <= budget or atomic(node):
            return [emit([node])]
        if not node.children:
            return split_leaf(node)
        result, pending = [], []

        def flush():
            if pending:
                result.append(emit(list(pending)))
                pending.clear()
        for child in node.children:
            if count_node(child) > budget:
                flush()
                result.extend(partition(child))
            else:
                if pending and count_group(node, pending + [child]) > budget:
                    flush()
                pending.append(child)
        flush()
        return result
    return partition(root)


def choose_budget(section_size, maximum, target, construct, *, native=False):
    """Select the best evaluated candidate by the main paper's Equation (11).

    ``native`` remains accepted for compatibility; all formats use one search.
    Binary probes generate candidates, without claiming a global optimum over
    unvisited budgets or assuming real-tokenizer counts are monotone.
    """
    if section_size <= 0:
        raise ValueError("section_size must be positive")
    upper = 2 * section_size - 1
    maximum = upper if maximum is None else maximum
    if not section_size <= maximum <= upper:
        raise ValueError("max_tree_budget must be in [C, 2C-1]")
    evaluated = {}

    def at(budget):
        if budget not in evaluated:
            evaluated[budget] = construct(budget)
        return evaluated[budget]

    def rank(budget):
        count = len(at(budget))
        return abs(count - target), int(count < target), budget

    at(section_size)
    at(maximum)
    low, high = section_size, maximum
    while low <= high:
        mid = (low + high) // 2
        if len(at(mid)) > target:
            low = mid + 1
        else:
            high = mid - 1
    for budget in (low, high):
        if section_size <= budget <= maximum:
            at(budget)
    selected = min(evaluated, key=rank)
    sections = evaluated[selected]
    for section in sections:
        section.target_flat_sections = target
        section.selected_tree_budget = selected
        section.tree_budget_max = maximum
        section.count_match_exact = len(sections) == target
        section.count_match_delta = abs(len(sections) - target)
        section.base_section_size = section_size
        section.candidate_budgets = sorted(evaluated)
    return sections
