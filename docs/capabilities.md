# Capabilities and review

For a worked explanation of where overrides came from, how metadata supports
them and how SPARQL displays the resulting assertions, see
[capability provenance](capability_provenance.md).

## Task model

A capability describes a **task**, such as `process / PDF document` or
`search / web`. A Skill or tool is a resource; an assertion is the association
between that resource and the task, supported by evidence. The model records
both the annotation method and its review status:

```text
Skill pdf ── candidate assertion ── process PDF document
                    └── description excerpt + SKILL.md source

Brave Search ── derived assertion ── search web
                    └── brave_web_search assertion + its source
```

The 17 assertions originating from static registrations are preserved.
Tools and Skills receive one or more tasks through manual overrides and automatic
proposals compiled into `config/capability_mappings.json`. Each mapping must match a passage in the
resource's own source description.
The name alone is insufficient; a mapping without supporting evidence remains unclassified.
Mappings are proposed by the project and marked `candidate_for_human_review`,
even when the source description is explicit.
A server's capabilities are derived from those of its tools through
`acg:derivedFromAssertion` links; this does not constitute runtime verification.

Following the latest enrichment:

- 10/10 servers have annotations derived from their tools;
- 55/55 tools have at least one candidate annotation;
- 109/110 Skills have a candidate annotation;
- `template-skill` remains unclassified because its description is placeholder text.

`Reviewed: 0` indicates that no annotation has been validated through human review.
These figures measure initial annotation coverage, not the complete set of capabilities
of each resource. Specific operations, formats, exclusions, and prerequisites may
still require more detailed annotation.

To examine annotations and their evidence:

- `reports/capabilities/review.csv`: tasks, methods, quotations, sources, and supporting assertions;
- `reports/capabilities/unclassified.csv`: resources without a justified mapping;
- `reports/capabilities/coverage.json`: detailed coverage by resource type.

Human review must check the task, the quoted passage, its restrictions, and the source.
`reports/capabilities/review.csv` is generated. Record persistent entity decisions through the [curation register](override_curation.md);
`config/capability_overrides.json` is the materialized input, not the editing interface.


## Automatic proposals as the corpus grows

There are three configuration roles:

- `config/capability_vocabulary.json`: reusable action/object concepts with matching
  patterns; Web/internet phrases share the `search web` concept.
- `config/capability_overrides.json`: materialized explicit rules checked against
  `data/curation/override_history.jsonl`; revisions use the curation commands.
- `config/capability_mappings.json`: generated artifact; safe to delete and rebuild.

`python pipeline.py import`, `build` and `run` regenerate mappings. Use
`python pipeline.py mappings` to regenerate them independently. SQLite must exist.
The extractor reads all stored Skill and tool descriptions, including resources
outside the RDF sample, and full Skill bodies imported into SQLite. Body matching
skips frontmatter, fenced examples, explicit Good/Bad/Example-labelled lines
and explicitly negative lines. Installation
commands are examined only under dedicated installation/setup headings.

Each vocabulary match records an exact quote, source URL and canonical entity ID.
A resource can have multiple proposals. RDF application checks the quote against
text from the same source and deduplicates identical entity/capability pairs.
Explicit negation earlier in the same clause excludes automatic matches.
This finite vocabulary misses many tasks; textual matching can still misinterpret
context. Matching evidence is not proof of runtime functionality.

Manual name-based mappings are retained alongside new proposals. Canonical entity
entries in `capability_overrides.json` replace that entity's proposals, allowing
reviewers to reject, correct or approve them. An entity entry is a list of rules:

```json
{
  "action": "search",
  "object": "web",
  "evidence_pattern": "Search the Web",
  "status": "reviewed"
}
```

The materialized format uses the full canonical entity URI as the key in `entities`.
Use [curation](override_curation.md) to record changes; nonempty entity lists
with per-rule body evidence still need an extended recording workflow. Copy the proposal's
source URL and origin to retain its source restriction. `rejected` rules are not
emitted; `reviewed` rules receive that RDF status only if evidence still matches.
Other rules remain candidates. An empty entity list suppresses automatic and
name-based proposals for that entity. Existing source-registration assertions are
independent and remain present; this override does not retract those assertions.
Derived server assertions remain candidates regardless of supporting review status.
`reports/capabilities/review.csv` is regenerated output, not a decision input.

Deleting the generated mappings does not delete the vocabulary or review decisions.
They are sufficient, together with SQLite, to recreate the artifact.

## Expanding the selected RDF sample

The database imports all accepted records, while the RDF sample stays frozen.
Change `additional_skill_count` in `config/corpus_selection.json`, then run:

```bash
python pipeline.py import --refresh-selection
python pipeline.py run
```

The initial corpus is retained; additional Skills must have eligible evidence.
An insufficient eligible pool raises an error. Server selection continues to
include registry servers with exposed tool evidence. Newly imported servers
without collected tools remain in the database, outside that RDF selection.


## Full-document evidence and evaluation

`pipeline.py import` stores available pinned Skill archives in the `skill_document`
table. It records source URL, revision, original decoded text, SHA-256, cache
locator and availability status. Registry markdown is accepted only when the
complete cached text matches the normalized content hash and pinned revision.
Frontmatter-only registry caches remain `body_not_cached` unless a verified
complete snapshot has been collected separately. Import and build do not perform
remote fetches; no text is assigned by Skill name alone.

The source body remains in SQLite so subsequent builds work without reopening
archives. Import is required once to migrate an older database. The independent
GitSkills statistics are not full-document input to this graph: their raw tables
are not present in the repository.

Body task matches carry exact quote, one-based line and zero-based Unicode
character offsets (end exclusive). The importer hashes the stored text encoded
as UTF-8; this fingerprint is an integrity locator, not a trust or safety score.
The builder checks the quote and fingerprint again before emitting an assertion.
Repeated matches for a task are available in generated mappings, while RDF
retains one selected assertion per entity/task rather than every occurrence.

Format mentions, requirement statements under dependency headings and installation
instructions become `acg:SkillFactAssertion` candidates. They are intentionally
separate from existing declared `acg:dependency` facts. A tool/package mention
is not interpreted as an unconditional requirement. Fact candidates currently
remain pending review; task overrides do not approve or retract these facts.
The new SHACL shapes check evidence structure and candidate kinds, not meaning.

Outputs:

- `reports/capabilities/documents.csv`: per-source body availability.
- `reports/capabilities/documents.json`: canonical Skill document coverage.
- `reports/capabilities/body_facts.csv`: all source-located fact candidates.
- `reports/capabilities/review.csv`: task assertions, now with body evidence locations.
- `data/evaluation/skill_body_review.csv`: small deterministic review worksheet.

The worksheet selects at most 12 entity/kind contexts on its first run and retains
previous labels on refresh. `current_candidate=false` identifies preserved
rows whose extraction is no longer active; do not include them in an evaluation
of the current extractor. The sheet is not a representative random sample. Fill
`decision` (`correct`, `incorrect`, or `uncertain`), `reviewer` and `notes` after
checking the source. No precision, recall or human-reviewed accuracy is reported
while labels remain pending. Worksheet labels are evaluation records; accepted
production task decisions require explicit recorded curation; worksheet labels
do not automatically modify the materialized overrides.


### Collecting missing bodies

```bash
python pipeline.py collect --source skill-documents
python pipeline.py run
```

The collector reads registered Skill identities from SQLite, accepts direct
`raw.githubusercontent.com` URLs with an exact 40-character commit revision,
and checks the downloaded bytes against the recorded SHA-256. It caps documents
at 2 MB, uses four concurrent downloads, and reuses valid cached files.
`--limit 20` restricts the collection to the first 20 eligible sources.

Snapshots are in `data/imports/registry/skill_documents/`, keyed by URL hash;
collection statuses are in `reports/capabilities/document_collection.json`.
Collection then synchronizes SQLite and regenerates mappings. A hash mismatch,
missing pinned URL or download error never becomes an accepted document. No
unversioned branch fallback is used. Source snapshots and selection fingerprints
are preserved. The 240-source collection on 2026-11-25 verified every file,
resulting in full documents for 243 distinct Skills after merging the original
archives; 32 secondary imports remain incomplete.


## Action-based discovery

CQ05 in [competency questions](competency_questions.md) groups tools by mapped
verbs such as `search`, `convert` and `list`. `tool_action_groups.rq` counts
canonical tools and servers; `tools_by_action.rq --action search` retains the
object and evidence. This uses current manual and automatic mappings, not a
complete grammatical analysis of all descriptions. Synonym normalization and
precision/coverage evaluation remain areas for further work.


## Fixed-vocabulary transition after the meeting

The [fixed SKOS v1 vocabulary](../ontology/capabilities_v1.ttl) contains 20 proposed
coarse concepts. See [LLM extraction](llm_extraction.md) for the versioned prompt,
closed-list selection, grouping proposals and endpoint preparation. The legacy
fine-grained tasks are retained for comparison; the full graph is not yet limited
to 20 concepts. Existing deterministic mappings are not represented as EURECOM
model results. Joint review is required before accepting the vocabulary as final.
