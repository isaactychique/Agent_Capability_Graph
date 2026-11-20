# Capabilities and review

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
`reports/capabilities/review.csv` is generated. Record persistent entity decisions
in `config/capability_overrides.json`, as described below.


## Automatic proposals as the corpus grows

There are three configuration roles:

- `config/capability_vocabulary.json`: reusable action/object concepts with matching
  patterns; Web/internet phrases share the `search web` concept.
- `config/capability_overrides.json`: persistent manual rules and entity decisions.
- `config/capability_mappings.json`: generated artifact; safe to delete and rebuild.

`python pipeline.py import`, `build` and `run` regenerate mappings. Use
`python pipeline.py mappings` to regenerate them independently. SQLite must exist.
The extractor reads all stored Skill and tool descriptions, including resources
outside the RDF sample. It does not parse complete SKILL.md bodies yet.

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

Use the full canonical entity URI as the key in `entities`. Copy the proposal's
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
