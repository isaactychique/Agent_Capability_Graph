# Competency questions v1 — Lin's proposal for joint review (26 November 2026)

This is a concrete 20-question proposal, **not a record of Isaac's agreement**.
The repository at `62bfd2521a` has four query files and three question bullets in
`docs/references/second_progress_report.pdf`; the meeting mentions approximately
12 questions, but a complete numbered list could not be located in this snapshot.
Existing questions are retained below. Numbering is proposed to make the agreed
first-half / second-half work split reviewable. Isaac should confirm CQ01–10 or
supply his existing list before joint finalization. Do not describe these as 20
validated retrieval tasks or gold-standard evaluation queries.

| ID / proposed owner | User question | Expected answer structure / existing model or gap |
|---|---|---|
| CQ01 Isaac | Which tools can search the Web, rather than fetch a known URL? | Tool + server + search/web capability + evidence + review status. Reuse `tools_for_web_search.rq`; Brave web search is a current example. |
| CQ02 Isaac | Which Skills are candidates for PDF processing? | Skill identity + description/capability + evidence. Reuse `skills_by_format.rq --format PDF`; description matches are candidates. |
| CQ03 Isaac | Which Skills are candidates for spreadsheet work? | Same structure, `--format spreadsheet`; xlsx is an existing test case. |
| CQ04 Isaac | Which servers expose file operations, and what access or installation constraints are documented? | Server + exposed tool + task + transport/install/access observations. Missing access is unknown. |
| CQ05 Isaac | What inputs are required and what output schema is recorded for a chosen tool? | Tool + inputSchema/outputSchema/requiredParameter; JSON literals need application-side JSON parsing, not invented parameter nodes. |
| CQ06 Isaac | Which servers expose resources or prompt templates? | Server + exposesResource/exposesPrompt + names. Empty results are allowed if not harvested. |
| CQ07 Isaac | What endpoint, transport and authentication information is recorded for a chosen server? | Server + transport/authentication + remote URL observation. Need confirm source field and mapping for endpoint; repository URL is not endpoint URL. |
| CQ08 Isaac | Which tools have a source-declared destructive or read-only hint? | Tool + exact hint + source; a hint is not proof of safety. Use destructiveHint/readOnlyHint. |
| CQ09 Isaac | Which Skills/tools share a normalized capability but differ in recorded dependencies or state-change hints? | Pair + shared concept + each recorded constraint; unknown is explicit. Requires joins, not label equality. |
| CQ10 Isaac | Which resources still lack a capability annotation or have only unreviewed annotations? | Resource + type + missing/candidate status. Reuse coverage logic; absence means unclassified, not incapable. |
| CQ11 Lin | Which Skills have recorded license information, and what source is retained? | Skill + value/status + exact observation source where available; direct projections are marked separately. |
| CQ12 Lin | Which Skills have recorded versions, preserving top-level versus metadata scope? | Skill + original field path + value + source/status; currently no rows. |
| CQ13 Lin | Which Skills have declared tags/categories that I can inspect before choosing? | Skill + raw tags/category + source/status; no assumption that a tag proves a capability. |
| CQ14 Lin | Who is the declared author of a Skill and where was attribution found? | Skill + raw author value + scope/source. Do not equate author and repository owner. |
| CQ15 Lin | Which tool permissions are declared for each Skill? | Skill + allowed-tools declaration; not effective runtime authorization. |
| CQ16 Lin | What environment or dependency requirements are recorded for each Skill? | Skill + compatibility/dependency + value/status. A blank is unknown. |
| CQ17 Lin | What explicit user/model invocation settings are recorded for Skills? | Separate user-invocable and disable-model-invocation values; preserve boolean/string distinction and host scope. |
| CQ18 Lin | What argument hints are available to guide Skill invocation? | Skill + raw hint + source/status; a hint is not a typed parameter schema. |
| CQ19 Lin | Which source and revision support a Skill's proposed capability? | Skill + capability + method/review status + exact assertion source + revision/evidence where recorded. |
| CQ20 Lin | Which distinct Skill identities share the same recorded name? | One unordered identity pair per exact RDF name match, with repository links. Different identities do not establish different behavior. |

## Relationship to the merged catalogue

This proposal retains its original local numbering. The maintained catalogue at
[queries/competency_questions.md](../../queries/competency_questions.md) contains
22 atomic questions under the 20 original topic IDs. Identical CQ numbers across
these two documents do not necessarily identify the same question. Joint review
must reconcile the proposals before treating them as one agreed list. Snapshot
observations below refer to the original audit, not a rerun after the merge.

## Lin's implemented half

Queries: `queries/nov26/cq11_*.rq` through `cq20_*.rq`.
Run from the repository root:

```sh
python pipeline.py query queries/nov26/cq15_allowed_tools.rq
python -m src.acg.ingestion.gitskills.query_audit
python -m unittest discover -s tests -v
```

Read `reports/nov26/query_audit.json` and CQ11–CQ20 CSVs for the exact fixed-graph
results. The audit records graph and query hashes. Query rows are not entity
counts. CQ11 deliberately keeps both an observation and a projection if both
exist: their provenance granularity differs. `representation=direct_projection`
leaves field-level source unbound rather than assigning every document linked to
the Skill as evidence for that particular value. CQ11–18 return checked-but-empty
observations as well as values; consult `rows_with_value`.

All ten queries have synthetic positive and negative cases. These are isolated
fixtures, never added to the research graph. They establish query behavior, not
real-world completeness or classifier accuracy. Queries operate on explicit
triples without OWL entailment. Top-level field paths and `metadata.*` remain
separate; this is also the proposed import contract for future metadata ingestion.
