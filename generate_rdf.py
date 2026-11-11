#!/usr/bin/env python3
"""Compatibility launcher for the SQLite-to-RDF pipeline."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from acg.generate_rdf import main


if __name__ == "__main__":
    main()
