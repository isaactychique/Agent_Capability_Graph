#!/usr/bin/env python3
"""Compatibility launcher for the keyword-search prototype."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from acg.search import main


if __name__ == "__main__":
    main()
