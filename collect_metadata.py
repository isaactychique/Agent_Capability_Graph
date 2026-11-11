#!/usr/bin/env python3
"""Compatibility launcher for the small metadata collection pilot."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from acg.collect_metadata import main


if __name__ == "__main__":
    main()
