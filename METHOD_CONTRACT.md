# Method contract

The four format adapters share Algorithm 1, structural path annotations,
final-section memory links, and the memory update interface.

## Inputs and section content

`build_sections(value, tokenizer, C, method, context_format="json")` accepts a
JSON-compatible value. JSON is serialized compactly with insertion order and
Unicode text retained. Both Flat and TreeAgent use this serialization.
`parse_json_text(raw_text)` accepts a single value or whitespace-separated
complete response documents. Multiple documents share a virtual ordered root;
each is serialized compactly and documents are separated by one newline, with
no added outer array brackets. Flat slices this combined text and TreeAgent
plans the entire forest with one budget, global section indices and memory
history. Paths `$[i]` identify document `i` under the virtual root; indices
inside each document keep their original meaning. The virtual root participates
in sibling grouping and final-section memory links. Fragment wrappers restore
only actual JSON ancestors, never the virtual root. A single document retains
the existing paths and serialization. Raw inputs remain available unchanged
for the separate InfMem retrieval corpus.
HTML, YAML, and JavaScript accept original source strings; their adapters use
pinned Tree-sitter parsers and preserve source order and bytes.

`planning.partition_tree` retains fitting subtrees, groups adjacent fitting
siblings, and recursively partitions oversized children. A JSON subtree is
serialized as its value; a sibling group is an object or array containing its
children. Native subtree budgets count their original parser spans, and native
sibling budgets count the span from the first through the last child.

## Leaf splitting and wrappers

Oversized JSON strings split into consecutive fragments with valid JSON quotes
and escapes. Surrogate pairs stay together. Prefix probes and bisection find a
measured fitting fragment. Before a continuation, the splitter prefers the latest
whitespace or sentence boundary whose serialized fragment fills at least 80%
of the content budget. This fill threshold is an implementation setting.

Each fragment restores its enclosing object keys and array brackets. These
wrappers contain the selected branch; original array positions remain in
`path_parts`. `content_text` holds the quoted leaf fragment, while `text` and
`raw_text` include its wrappers. Concatenating the decoded `content_text` values
restores the original string. Intact JSON subtrees retain their own serialization.

Native rendering attaches surrounding source syntax to the selected content:
preceding syntax goes to the first descendant, gaps to subsequent units, and
closing syntax to the last descendant. Joining native section texts reconstructs
the original input byte-for-byte.

For wrapped sections:

```text
text = wrapper_prefix + content_text + wrapper_suffix
```

`content_tokens` counts the budgeted content. `wrapper_tokens` counts the prefix
and suffix separately. `total_tokens` counts the rendered text plus the separately
encoded path. Wrappers, paths, retrieved memory, and native context enter the
host's request accounting separately from the section-content budget.

HTML text, plain YAML strings, and JavaScript literal strings support safe
continuations. JSON non-string leaves, YAML block/quoted/typed scalars and aliases,
HTML script/style content, and undecomposed JavaScript expressions remain atomic.
Atomic units exceeding the content budget carry `atomic_overflow=true`.
Malformed YAML and JavaScript raise an error; HTML recovery retains uncertain
spans atomically.

## Budget search

Let `N` be Flat's section count. Candidate comparisons use
`(abs(n(B)-N), n(B)<N, B)`: smaller count error, a count at least `N`, then smaller
budget. Counts are cached, and budgets remain in `[C, 2*C-1]`.

All four formats evaluate both endpoints, binary-search probes toward
`n(B) <= N`, and the final in-range budget and predecessor. Select the best
of **all** evaluated candidates, including earlier probes, using the main
paper's Equation (11) and tie rules. Binary probes generate candidates;
the selection rule also applies if measured counts are nonmonotone.

Plans record evaluated candidates, selected budget, count difference, and whether
counts match. Token counts come from the supplied tokenizer; the paper's
additive-length analysis uses its stated integer-leaf model.

## Paths and memory links

The root path is `()` and renders as `$` for JSON/YAML or `/` for HTML/JavaScript.
Subtree and leaf-fragment paths follow original ancestors. A sibling group uses
its parent's path and zero-based inclusive positions, such as
`$.records::children[0,2]`. A range annotation is metadata attached to the section.
Native parsers retain HTML element/text structure, YAML mappings/sequences/stream
documents, and JavaScript static statement/member/property/element structure.
JavaScript is parsed without execution; YAML aliases remain literal syntax.

`annotate_tree_links` assigns each node its final content-section index `ell(v)`.
Descendants of an intact subtree share its index; split leaves end at their last
fragment. For every parent-child edge, add `(ell(child), ell(parent))` when the
source index is strictly smaller. The root participates. Parents ending at the
same section contribute a union of source indices, deduplicated by index.

## Memory updates and residual retrieval

`run_memory_agent` retrieves linked spans, obtains native context, calls the host
update, and saves the resulting memory under the one-based section index.
After processing the sections, it calls the host answer procedure. The host
provides model calls and internal control actions through these callbacks.

`ResidualMemoryStore` accepts linked states already saved before the current
update. Spans are split at line and sentence boundaries. Terms are case-normalized,
split at camel-case and underscore boundaries, and filtered with the fixed
function-word list in `residual.py`. The score is multiset term overlap plus
`0.25` per distinct overlapping term. Ties prefer the earlier source section,
then earlier span. Only span text contributes to the score.

Zero-score spans are discarded. At most four spans are selected across the
combined candidates, then each is clipped to 96 tokens. Their texts are joined
with newlines. Empty links or zero positive matches yield an empty residual.
Each updated memory is saved, including updates for intermediate leaf fragments.

## InfMem retrieval

`build_infmem_retrieval_corpus(raw_text, tokenizer)` constructs 500-token chunks
with 100-token overlap inside canonical 5,000-token raw windows. Pass the original
input, including JSON whitespace, before structural serialization. Flat and
TreeAgent use the same corpus and host BM25 settings. Raw-window indices and
token offsets support host exclusion rules independently of structural sections.
The host supplies its BM25 index, retrieval controller, and stopping logic.
Native retrieval contributes to `Observation.native_context`; linked-memory
retrieval contributes to `Observation.residual`.

## Answer scoring

`evaluation.replay` scores already-extracted answers. Text matching normalizes
case and surrounding formatting. Numerical answers are parsed as complete
scalars; tolerance is `max(0.01, 0.001 * abs(gold))`. Standard currency formatting
and number words are supported. A currency code in the reference must be present
in the prediction. Records selecting `exact_number_match` compare finite decimal
scalars exactly. Empty answers and malformed JSON lists receive zero.

Ordered tasks compare corresponding positions. Unordered list tasks use maximum
one-to-one matching with the same numerical tolerance and retain multiplicity.
Numerical signs and literal trailing hyphens are preserved; only leading bullet
markers followed by whitespace are removed. Partial credit divides matches by the larger
list length. Empty slots retain their positions and count toward list length;
they cannot match an answer value. For example, `["a", ""]` against `["a"]`
scores `0.5`. `analysis.macro_by` groups scored rows for equal-weight aggregation.

`code/evaluation/README.md` defines replay input fields and gives a runnable
example. API source examples retain their source `answer_protocol` and JSON
answer types; their inspection command is in `data/json/README.md`.
