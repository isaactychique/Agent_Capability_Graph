#!/usr/bin/env python3
"""Compatibility command; implementation: acg.ingestion.curated."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from acg.ingestion.curated import main

if __name__ == "__main__":
    main()
