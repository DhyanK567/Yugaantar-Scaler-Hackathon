"""MediLocker Offline-First Local Application Launcher.
Manages configuration, storage checks, SQLite migrations, single-instance locking,
loopback-only FastAPI + Next.js startup, health checks, browser launch, and clean shutdown.
"""
from __future__ import annotations

import argparse
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path
from typing import List, Optional

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
LOCK_FILE = DATA_DIR / "medilocker.lock"
BACKEND_HOST = "127.0.0.1"
BACKEND_PORT = int(os.environ.get("MEDILOCKER_BACKEND_PORT", "8000"))
FRONTEND_HOST = "127.0.0.1"
FRONTEND_PORT = int(os.environ.get("MEDILOCKER_FRONTEND_PORT", "3001"))


def _is_port_in_use(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((host, port)) == 0


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def acquire_instance_lock() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if LOCK_FILE.exists():
        try:
            old_pid = int(LOCK_FILE.read_text(encoding="utf-8").strip())
            if _pid_alive(old_pid):
                raise RuntimeError(
                    f"Another MediLocker instance is already running (PID {old_pid}). "
                    f"Stop it first or remove {LOCK_FILE} if stale."
                )
        except ValueError:
            pass
    LOCK_FILE.write_text(str(os.getpid()), encoding="utf-8")


def release_instance_lock() -> None:
    try:
        if LOCK_FILE.exists():
            LOCK_FILE.unlink()
    except OSError:
        pass


def verify_storage_and_db() -> None:
    for d in (DATA_DIR, DATA_DIR / "datasets", DATA_DIR / "jobs"):
        d.mkdir(parents=True, exist_ok=True)
        probe = d / ".write_test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()

    if str(ROOT_DIR) not in sys.path:
        sys.path.insert(0, str(ROOT_DIR))
    from backend.database import init_db

    init_db()


def flush_database() -> None:
    try:
        if str(ROOT_DIR) not in sys.path:
            sys.path.insert(0, str(ROOT_DIR))
        from backend.database import get_db

        with get_db() as conn:
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
    except Exception:
        pass


def wait_for_http(url: str, timeout_secs: int = 30) -> bool:
    deadline = time.monotonic() + timeout_secs
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1.5) as resp:
                if 200 <= resp.status < 400:
                    return True
        except Exception:
            time.sleep(0.4)
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="MediLocker Offline-First Local Launcher")
    parser.add_argument("--no-browser", action="store_true", help="Do not open browser automatically")
    parser.add_argument("--check-only", action="store_true", help="Verify config, storage, DB, and ports then exit")
    args = parser.parse_args()

    version_file = ROOT_DIR / "VERSION"
    version = version_file.read_text(encoding="utf-8").strip() if version_file.exists() else "2.0.0"
    print(f"=== MediLocker {version} (Offline-First Loopback Mode) ===")

    try:
        acquire_instance_lock()
        verify_storage_and_db()
    except Exception as exc:
        print(f"[ERROR] Startup preflight failed: {exc}", file=sys.stderr)
        return 1

    if _is_port_in_use(BACKEND_HOST, BACKEND_PORT):
        print(
            f"[ERROR] Port {BACKEND_PORT} on {BACKEND_HOST} is already occupied. "
            "Close the conflicting process and retry.",
            file=sys.stderr,
        )
        release_instance_lock()
        return 1

    if _is_port_in_use(FRONTEND_HOST, FRONTEND_PORT):
        print(
            f"[ERROR] Port {FRONTEND_PORT} on {FRONTEND_HOST} is already occupied. "
            "Close the conflicting process and retry.",
            file=sys.stderr,
        )
        release_instance_lock()
        return 1

    if args.check_only:
        print("[OK] Configuration, storage, SQLite DB, and loopback ports verified.")
        release_instance_lock()
        return 0

    frontend_dir = ROOT_DIR / "frontend"
    next_cmd = frontend_dir / "node_modules" / ".bin" / ("next.cmd" if os.name == "nt" else "next")
    if not (frontend_dir / ".next").exists() or not next_cmd.exists():
        print(
            "[ERROR] Frontend production build (.next) not found. Run 'pnpm build' in frontend/ first.",
            file=sys.stderr,
        )
        release_instance_lock()
        return 1

    env = dict(os.environ)
    env.setdefault("RAKSHA_SECRET", "practice")
    env["MEDILOCKER_OFFLINE_MODE"] = "true"
    env["HF_HUB_OFFLINE"] = "1"
    env["TRANSFORMERS_OFFLINE"] = "1"
    env["FRONTEND_ORIGINS"] = f"http://{FRONTEND_HOST}:{FRONTEND_PORT},http://localhost:{FRONTEND_PORT}"

    procs: List[subprocess.Popen] = []

    def shutdown(*_args):
        print("\n[MediLocker] Shutting down local services...")
        for p in procs:
            if p.poll() is None:
                p.terminate()
        for p in procs:
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                p.kill()
        flush_database()
        release_instance_lock()
        print("[MediLocker] Database flushed. Completed jobs and audit history preserved.")

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    try:
        print(f"[1/2] Starting FastAPI backend on http://{BACKEND_HOST}:{BACKEND_PORT} ...")
        backend_proc = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "backend.main:app",
                "--host",
                BACKEND_HOST,
                "--port",
                str(BACKEND_PORT),
            ],
            cwd=str(ROOT_DIR),
            env=env,
        )
        procs.append(backend_proc)

        if not wait_for_http(f"http://{BACKEND_HOST}:{BACKEND_PORT}/api/health", timeout_secs=25):
            print("[ERROR] Backend failed health check.", file=sys.stderr)
            shutdown()
            return 1
        print("[OK] Backend healthy.")

        print(f"[2/2] Starting Next.js UI on http://{FRONTEND_HOST}:{FRONTEND_PORT} ...")
        frontend_proc = subprocess.Popen(
            [str(next_cmd), "start", "-H", FRONTEND_HOST, "-p", str(FRONTEND_PORT)],
            cwd=str(frontend_dir),
            env=env,
        )
        procs.append(frontend_proc)

        if not wait_for_http(f"http://{FRONTEND_HOST}:{FRONTEND_PORT}", timeout_secs=25):
            print("[ERROR] Frontend failed to respond on loopback.", file=sys.stderr)
            shutdown()
            return 1
        print(f"[OK] MediLocker ready at http://{FRONTEND_HOST}:{FRONTEND_PORT}/login")

        if not args.no_browser:
            webbrowser.open(f"http://{FRONTEND_HOST}:{FRONTEND_PORT}/login")

        print("Press Ctrl+C to stop MediLocker cleanly.")
        while all(p.poll() is None for p in procs):
            time.sleep(1)

    finally:
        shutdown()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
