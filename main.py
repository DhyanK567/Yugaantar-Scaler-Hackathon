#!/usr/bin/env python3
"""Root-level entrypoint for MediLocker / GuptKavach Privacy Engine.

Delegates directly to starter/main.py without duplicating any privacy engine logic.
"""
from __future__ import annotations

import runpy
import sys
from pathlib import Path

STARTER_MAIN = Path(__file__).resolve().parent / "starter" / "main.py"

if __name__ == "__main__":
    starter_dir = str(STARTER_MAIN.parent)
    if starter_dir not in sys.path:
        sys.path.insert(0, starter_dir)
    runpy.run_path(str(STARTER_MAIN), run_name="__main__")
