# November 26 meeting follow-up

## Status

| Meeting action | Current local deliverable | Remaining work |
| --- | --- | --- |
| Source names, links, ontology and questions for Mattermost | `data_sources.md`, including a message draft | Publish files and post after authorization |
| Approximately 22 atomic competency questions | `competency_questions.md`, 22 atomic proposals retaining the 20 original topic IDs | Joint wording/model review with Lin |
| First-half SPARQL review batch | CQ01–CQ10 executable formulations; query coverage report | GitHub PR and Lin review |
| Second-half batch | CQ11–CQ20 executable drafts for discussion | Lin ownership/revision and reciprocal review; not presented as Lin's completed work |
| Fixed vocabulary v1, 15–25 concepts | `ontology/capabilities_v1.ttl`, 20 concepts and auditable grouping CSV | Resolve 23 ambiguous and 18 unmatched detailed concepts; joint vocabulary approval |
| Unclassified Skill investigation | `template-skill` confirmed to contain placeholder text | Retain abstention; decide whether templates belong in later evaluation corpus |
| Versioned extraction prompt | `prompts/capability_extraction_v1.txt`, examples and allowed vocabulary injected per request | Joint prompt review; historical ChatGPT prompt is unavailable |
| Automated EURECOM extraction | Offline request preparation, explicit API adapter, response validation and RDF integration | Endpoint/model/API confirmation, actual model run and review |
| Additional metadata analysis | Existing `reports/gitskills/` tables are preserved and linked | Lin's field semantics and joint ontology decisions |
| December baseline evaluation | Protocol outlined in `llm_extraction.md` | Gold relevance judgments and implemented comparison runs |

## Recorded local executions

- 22 atomic competency questions, 25 instantiations (two formats and three bundle kinds):
  all executed without query errors. See `reports/queries/competency_coverage.csv`.
- Empty resource, prompt and risk-signal results are expected collection gaps.
- 20 SKOS concepts; grouping proposals cover all 154 detailed concepts currently
  in the graph, not a reconstructed historical 149-node list.
- Five selected Skills produced eight offline LLM request packets. No EURECOM
  model was contacted and there are no model-derived benchmark scores.
- The normal pipeline still builds 7,751 triples and 221 capability assertions;
  structural SHACL passes and the placeholder Skill remains a coverage warning.

## Placeholder investigation

Canonical entity: `urn:acg:metadata:skill/skl_9a1909e129974f5d1a395981`.
Name: `template-skill`. Path: `template/SKILL.md` in `anthropics/skills`, revision
`2c5958ecac7cee2b583967a2c4981d0f4a75c579`.
Description: "Replace with description of the skill and when Claude should use it."
It is a template, not a documented task-bearing Skill. Forcing classification
would add unsupported knowledge. Keep it visible as a negative/abstention example;
do not silently change the selected sample to make coverage appear complete.

## Publication boundary

These new deliverables are local and have not been submitted in a GitHub PR.
No Mattermost message has been sent. The local environment currently has no GitHub CLI installed or connected
GitHub tool for PR creation. Git publishing and reviewer assignment
remain explicit follow-up steps. Public w3id registration is lower priority than
the agreed vocabulary, queries, endpoint integration and evaluation preparation.
