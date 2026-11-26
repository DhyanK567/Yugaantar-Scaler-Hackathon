"""Runner and evaluator for the Phase 2 adversarial benchmark."""
from __future__ import annotations

import base64
import json
import os
import re
import shutil
import subprocess
import sys
import unicodedata
from pathlib import Path

from generate_corpus import build_adversarial_corpus

REPO_ROOT = Path(__file__).resolve().parents[2]
ADV_DIR = Path(__file__).resolve().parent


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKC", s)
    s = re.sub(r"[\u200b-\u200d\ufeff]", "", s)
    return " ".join(s.casefold().split())


def _collect_all_text(out_dir: Path) -> tuple[str, str]:
    san_parts, all_parts = [], []
    for p in sorted(out_dir.rglob("*")):
        if p.is_file():
            all_parts.append(p.name)
            txt = p.read_text(encoding="utf-8", errors="replace")
            all_parts.append(txt)
            # Decode any base64 runs
            for m in re.finditer(r"[A-Za-z0-9+/]{24,}={0,2}", txt):
                try:
                    all_parts.append(base64.b64decode(m.group(0)).decode("utf-8", errors="ignore"))
                except Exception:
                    pass
            if "sanitized" in p.parts:
                san_parts.append(p.name)
                san_parts.append(txt)
                for m in re.finditer(r"[A-Za-z0-9+/]{24,}={0,2}", txt):
                    try:
                        san_parts.append(base64.b64decode(m.group(0)).decode("utf-8", errors="ignore"))
                    except Exception:
                        pass
    return _norm("\n".join(san_parts)), _norm("\n".join(all_parts))


def main() -> int:
    truth = build_adversarial_corpus(ADV_DIR)
    inp = ADV_DIR / "input"
    out = ADV_DIR / "output"
    if out.exists():
        shutil.rmtree(out)

    env = dict(os.environ, RAKSHA_SECRET="adv_test_secret_2026")
    proc = subprocess.run(
        [sys.executable, str(REPO_ROOT / "starter" / "main.py"), "--input", str(inp), "--output", str(out)],
        env=env,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        print("ENGINE FAILED:", proc.stderr)
        return 1

    val = subprocess.run(
        [sys.executable, str(REPO_ROOT / "validate_output.py"), "--input", str(inp), "--output", str(out)],
        capture_output=True,
        text=True,
    )
    print("Validator:", val.stdout.strip())

    san_text, all_text = _collect_all_text(out)
    report = json.loads((out / "report.json").read_text(encoding="utf-8"))

    # False negatives (missed PII)
    missed_pii = [item for item in truth["must_redact"] if _norm(item) in san_text]
    # Check relative Ramesh specifically ("s/o ramesh" must not survive)
    if "s/o ramesh" in san_text:
        missed_pii.append("S/o Ramesh")

    # Canary leaks anywhere in output
    missed_canaries = [c for c in truth["canaries"] if _norm(c) in all_text]

    # False positives (damaged clinical utility / meaning traps)
    lost_clinical = [item for item in truth["must_preserve"] if _norm(item) not in san_text]

    # Quarantine check
    q_count = report["counts"]["files_quarantined"]

    print(f"\n=== ADVERSARIAL BENCHMARK REPORT ===")
    print(f"Files sanitized: {report['counts']['files_sanitized']} | Quarantined: {q_count} (expected {truth['must_quarantine_count']})")
    print(f"Missed PII (False Negatives): {len(missed_pii)} / {len(truth['must_redact']) + 1}")
    for m in missed_pii:
        print(f"  [FN] {m}")
    print(f"Leaked Canaries: {len(missed_canaries)} / {len(truth['canaries'])}")
    for c in missed_canaries:
        print(f"  [CANARY] {c}")
    print(f"Lost Clinical / Meaning Traps (False Positives): {len(lost_clinical)} / {len(truth['must_preserve'])}")
    for l in lost_clinical:
        print(f"  [FP] {l}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
