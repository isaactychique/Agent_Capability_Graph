"""Project paths: source snapshots remain stable for provenance and selection hashes."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GRAPH = ROOT / 'data/processed/agent_capability_graph.ttl'
ONTOLOGY = ROOT / 'ontology/acg.ttl'
SHAPES = ROOT / 'ontology/shapes.ttl'
COVERAGE_SHAPES = ROOT / 'ontology/coverage.ttl'
REGISTRY = ROOT / 'metadata'
NORMALIZED = REGISTRY / 'data/normalized'
SELECTION = ROOT / 'config/corpus_selection.json'
REPORTS = ROOT / 'reports'
