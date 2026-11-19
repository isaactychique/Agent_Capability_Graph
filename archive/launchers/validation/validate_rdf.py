#!/usr/bin/env python3
"""Compatibility command; implementation: acg.validation."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from acg.validation import main

if __name__ == "__main__":
    main()
