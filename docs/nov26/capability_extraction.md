# Capability extraction handoff

Lin supplies `prompts/capability_extraction_description_v1.txt` and
`src/acg/capability_prompt.py`. This is an offline prompt/response contract, not a
claim that EURECOM inference was run. Isaac still owns vocabulary clustering;
the original handoff was based on the earlier graph snapshot. After merging,
`ontology/capabilities_v1.ttl` provides a draft 20-concept vocabulary using URNs;
it is not accepted by this HTTPS-only renderer until namespace alignment.

The renderer accepts a SKOS ConceptScheme with 15–25 concepts, HTTPS identifiers,
labels, definitions and optional scope notes. It embeds the **actual vocabulary**,
using the input file SHA-256 as vocabulary version. HTTPS is a proposed publishing
contract aligned with the professor's URI feedback, subject to joint namespace
agreement; it does not silently migrate the existing graph's URNs.
[SKOS reference](https://www.w3.org/TR/skos-reference/)

```sh
python -m src.acg.capability_prompt \
  --vocabulary /path/to/isaac-reviewed-vocabulary.ttl \
  --resource /path/to/resource.json \
  --output /path/to/rendered-prompt.txt
```

Resource JSON needs `resource_id` and `description`. Source identifiers/revisions
can be included, but must be retained by the calling pipeline independently of
model output. The examples use a clearly synthetic three-concept vocabulary to
illustrate matching, exclusions, multiple labels, missing evidence, out-of-scope
tasks and instruction injection. They are not production concepts.

The response validator rejects invented concept IDs, duplicate assignments,
nonmatching resource/vocabulary IDs, fabricated evidence substrings, malformed
objects and status/assignment inconsistencies. Passing these checks does not
establish semantic correctness; a model can quote a negated passage incorrectly.
Store outputs as candidate assertions, then manually review a stratified sample.
Suggestions go to a review queue and never expand the controlled list automatically.

Before endpoint integration (owner remains TBD), obtain EURECOM endpoint URL,
authentication mechanism, model identifier and allowed data scope through the
project's normal channel. No credentials were supplied or sought from unrelated
local files. Record model, prompt hash, vocabulary hash, source revision, decoding
parameters and timestamps. Use bounded retries/timeouts and resumable per-resource
outputs; never replace a reviewed mapping with an automatic candidate. Keep the
existing extractor selectable until the new pipeline is evaluated.

For December evaluation, freeze graph/corpus and task-oriented queries first;
prepare independently reviewed expected answers and compare KG, keyword, tags and
embedding baselines on the same candidates. Split vocabulary/prompt tuning tasks
from held-out evaluation tasks. Report precision@k, recall@k and a precisely defined
hit@k (at least one relevant item), not an ambiguous 'top-k accuracy'. CQ smoke-test
row counts are not those retrieval metrics.

## Merge integration note

This description-only contract uses `capability_extraction_description_v1.txt`
and returns `assignments` with concept URIs. The active pipeline uses
`capability_extraction_v1.txt` through `src/acg/llm_extraction.py`, returning
`selected` concept IDs with exact character offsets over document chunks.
The formats are intentionally kept separate: responses cannot be interchanged.
Both proposals remain available for joint review; this merge does not establish
a live endpoint run or approval of either classification vocabulary.
