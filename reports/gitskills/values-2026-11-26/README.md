# Additional-field values

See [analysis and ontology recommendations](../../../docs/nov26/metadata_mapping.md).
These aggregates extend the pinned GitSkills analysis, not the selected RDF corpus.

- `field_summary.csv`: present fields (including empty/invalid types), parsed denominator and distinct serialized values.
- `value_types.csv`: YAML type counts; exact reconciliation with the earlier report.
- `value_groups.csv`: all lexical/syntactic groups; overlapping groups must not be summed as disjoint partitions.
- `top_values.csv`: top 20 exact serialized values per field/scope; strings, booleans and lists remain distinct.
- `examples.csv`: deterministic evidence examples for the ten largest groups per field, with Git blob links and truncation flags.
- `manifest.json`: pinned dataset, parser version, source manifest, reconciliation and analysis script hash.

Group denominators count field-present contents. Field-presence denominators count
parsed mappings. Neither denominator describes all GitHub Skills or runtime usability.
