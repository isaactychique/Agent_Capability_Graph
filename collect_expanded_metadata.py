#!/usr/bin/env python3
"""Compatibility launcher for the expanded metadata collector."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from acg.collect_expanded_metadata import main


if __name__ == "__main__":
    main()
