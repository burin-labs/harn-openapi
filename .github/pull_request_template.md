<!--
Title: [Area] Sentence case description, for example
"[Parser] Preserve $ref siblings on resolved schemas".
Area is one of: Parser, Types, Codegen, Adapters, Connector, Fixtures,
Packaging, CI, Docs, Tests. See the title convention in AGENTS.md.

Body: 3-5 sentences total. What changed, why, the one risk, and how you
verified it, at the claim level. Do not list the gate commands; the Checks tab
already shows those. Replace the example below with your own.
-->

Preserves sibling keywords next to a `$ref` when a schema is resolved, because
JSON Schema 2020-12 treats `$ref` as one keyword among many rather than as a
replacement for the whole schema. Before this, a resolved schema silently lost
its `description` and `default`, so generated SDK source dropped doc comments
that the source document actually carried. The risk is that a document relying
on the older draft-07 reading, where siblings are ignored, now generates
different output, which shows up as a changed fixture diff rather than as a
parse failure. Verified by regenerating from the pinned Notion fixture and
confirming the operation and schema counts are unchanged while the recovered
descriptions appear in the generated source.

Closes #123 items: 1, 2 | Single-ask: #123
