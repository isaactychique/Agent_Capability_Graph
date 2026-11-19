#!/usr/bin/env python3
"""Project command. Implementation lives in src/acg/cli.py."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent / 'src'))
from acg.cli import main

if __name__ == '__main__':
    main()
