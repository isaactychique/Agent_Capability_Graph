"""Project paths: source snapshots remain stable for provenance and selection hashes."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GRAPH = ROOT / 'data/processed/agent_capability_graph.ttl'
ONTOLOGY = ROOT / 'ontology/acg.ttl'
SHAPES = ROOT / 'ontology/shapes.ttl'
COVERAGE_SHAPES = ROOT / 'ontology/coverage.ttl'
DATABASE = ROOT / 'data/acg.sqlite3'
IMPORTS = ROOT / 'data/imports'
CURATED_IMPORT = IMPORTS / 'curated/records.json'
REGISTRY = IMPORTS / 'registry'
NORMALIZED = REGISTRY / 'normalized'
SELECTION = ROOT / 'config/corpus_selection.json'
REPORTS = ROOT / 'reports'


def raw_path(record):
    """Resolve a source-relative cache locator without rewriting historical evidence."""
    return REGISTRY / record['raw_file'].removeprefix('data/')
