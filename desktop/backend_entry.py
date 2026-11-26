"""Frozen & Local Desktop Entrypoint for MediLocker Backend + Offline Privacy Engine.
Supports:
  1. --run-engine --input <dir> --output <dir>  (executes starter/main.py offline engine)
  2. --host 127.0.0.1 --port <port>             (runs FastAPI backend via Uvicorn)
"""
from __future__ import annotations

import argparse
import hashlib
import os
import sys
from pathlib import Path

# Python 3.14 + ReportLab md5 compatibility shim
_orig_md5 = hashlib.md5


def _safe_md5(*args, **kwargs):
    kwargs.pop("usedforsecurity", None)
    return _orig_md5(*args, **kwargs)


hashlib.md5 = _safe_md5  # type: ignore[assignment]


def _resolve_root() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent.parent


def main() -> int:
    root = _resolve_root()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    if "--run-engine" in sys.argv:
        starter_dir = root / "starter"
        if str(starter_dir) not in sys.path:
            sys.path.insert(0, str(starter_dir))
        sys.argv = [str(starter_dir / "main.py")] + [
            a for a in sys.argv[1:] if a != "--run-engine"
        ]
        import main as starter_main  # type: ignore

        return int(starter_main.main() or 0)

    parser = argparse.ArgumentParser(description="MediLocker Desktop Backend Server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    # Enforce loopback-only binding
    if args.host not in ("127.0.0.1", "localhost"):
        raise SystemExit("Desktop backend must bind strictly to 127.0.0.1")

    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    os.environ.setdefault("MEDILOCKER_OFFLINE_MODE", "true")

    import uvicorn
    from backend.main import app

    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
