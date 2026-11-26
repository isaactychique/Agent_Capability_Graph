# Fixed-vocabulary LLM extraction

Status on 2026-11-26: implemented request preparation, opt-in OpenAI-chat adapter,
response validation and build integration; **no EURECOM endpoint has been called**.
Endpoint URL, model name and API format still need confirmation. The original
ChatGPT experiment prompt is not present in the repository; the prompt here is
a new versioned artifact, not a reconstruction of that historical experiment.

## Vocabulary and clustering

`ontology/capabilities_v1.ttl` defines a draft scheme with 20 selectable SKOS
concepts, English labels, definitions and scope notes. Its scope is software-agent
information retrieval, files/documents, development, cloud/data operations and
supporting tasks. Its provisional URIs remain local URNs until the public
namespace migration; the w3id prefix is not registered yet.

`config/capability_clusters_v1.json` proposes lexical groupings of detailed task
labels. Run `pipeline.py vocabulary` to regenerate `reports/vocabulary/`.
The current 154 detailed concepts yield 113 single-match candidates, 23 ambiguous
and 18 unresolved. These are not completed human-reviewed clusters. The meeting
record's 149 concepts refer to an earlier snapshot. Every current concept is
included in the correspondence table, including unresolved cases.

The 20-concept scheme is a proposed v1 for joint approval with Lin, not a final
consensus. Detailed legacy tasks remain in the graph to preserve their evidence
and allow comparison. LLM selections use only the fixed list. Suggestions are
stored separately and never mint a new capability automatically. New fixed-v1
assertions can coexist with legacy assertions during this transition; the complete
KG is therefore not claimed to contain only 20 capability nodes.

The scheme uses `skos:ConceptScheme`, `skos:Concept`, `skos:inScheme`, labels,
definitions and scope notes as described in the
[W3C SKOS Reference](https://www.w3.org/TR/skos-reference/). No semantic equivalence
between fine-grained tasks and broad categories is asserted from a lexical match.

## Prepare the prompt and inputs offline

```bash
.venv/bin/python pipeline.py vocabulary
.venv/bin/python pipeline.py extract-capabilities --prepare --limit 5
```

Remove `--limit` to prepare all selected Skills. Full bodies are preferred;
descriptions are a fallback. Inputs come from the canonical database. Documents
are chunked into non-overlapping 8,000-character blocks; boundary-spanning evidence
can be missed. Each job records the prompt, vocabulary, identity, source, revision,
document hash and absolute chunk offset. A job ID hashes its complete messages.
The sample execution prepared 8 requests for 5 Skills; this is not a model result.

Prompt: `prompts/capability_extraction_v1.txt`.
Requests: `reports/llm/requests.jsonl`. Source instructions are treated as data.
The response must contain selected IDs, exact quotes and offsets, an optional
suggestion list, and an abstention reason. Unknown IDs, repeated IDs, invalid JSON
or mismatching evidence offsets are rejected. Provenance validity does not prove
that the selected category is semantically correct.

## Live execution — requires endpoint confirmation

Only the explicit `openai-chat` adapter is implemented. If EURECOM exposes a
different protocol, add its adapter after obtaining its contract. Do not infer
compatibility from the endpoint name. Once compatibility has been confirmed,
set these variables in the local shell, using the actual endpoint/model:

- `ACG_LLM_ENDPOINT`: full HTTPS chat-completions URL.
- `ACG_LLM_MODEL`: exact available model name.
- `ACG_LLM_API_KEY`: optional bearer credential; never commit or paste it in chat.

```bash
.venv/bin/python pipeline.py extract-capabilities --run --api-format openai-chat
.venv/bin/python pipeline.py run
```

`pipeline.py run` alone does not call a remote model. It consumes validated saved
responses when present. Extraction must be requested explicitly. Temperature is
set to zero; this is not a guarantee of reproducibility across server/model changes.

Saved artifacts include request inputs, raw responses, validated selections and
error types under timestamped `reports/llm/runs/`. `validated.jsonl` is the latest
run consumed by the builder. Credentials are not stored in those artifacts.
Failures are reported and partial results are explicit; an empty selection is
abstention, not a new catch-all category.

The builder rechecks current vocabulary, prompt/job identity, source hash and
quote offsets against SQLite before applying a saved response. It emits only
candidate assertions with the fixed SKOS concept, recorded model, source and
location. SHACL checks scheme membership. `perform / <category label>` denotes
a coarse fixed-v1 category; legacy action/object tasks retain their original scope.
Suggestions require joint manual review before any vocabulary version change.

## December evaluation plan

Freeze a corpus snapshot, task-oriented query list and manually judged expected
resource sets before tuning. Compare KG retrieval with keyword, source-tag and
embedding baselines on the same candidate corpus. Missing source tags are missing
features, not negative relevance labels. Use a development/test split and freeze
embedding model, normalization, ranking and tie handling.

Report precision, recall, precision@k, recall@k and hit@k with explicit denominators;
clarify whether "top-k accuracy" means at least one relevant answer in the top k.
Do not conflate query executability or SHACL conformity with retrieval quality.
Inspect failures due to missing documents, insufficient evidence, overly broad
categories, lexical ambiguity and ranking. No baseline comparison scores have
been measured yet; the existing small extraction worksheet is not a retrieval
benchmark or a representative accuracy estimate.

## Separate contract preserved after the merge

Lin's `src/acg/capability_prompt.py` reads
`prompts/capability_extraction_description_v1.txt`. It expects description-only
inputs and returns `assignments` with concept URIs, unlike the active pipeline's
`selected` IDs and document offsets. Its HTTPS-only vocabulary loader does not
yet accept the draft scheme's URNs. It is an independent offline proposal for
review, not the adapter invoked by `pipeline.py extract-capabilities`.
See [handoff](nov26/capability_extraction.md). No live EURECOM execution is implied
by the presence of either contract.
