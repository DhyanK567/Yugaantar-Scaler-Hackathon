"""Offline HTML Report Generator for GuptKavach Privacy Passport.

Produces a self-contained `privacy_passport.html` with zero external CDN,
font, or network dependencies.
"""
from __future__ import annotations

import html
from typing import Any


def _esc(val: Any) -> str:
    return html.escape(str(val), quote=True)


def _badge_class(status: str) -> str:
    s = str(status).upper()
    if s in ("PASS", "SIGNED", "VERIFIED", "EXECUTED", "TRUE"):
        return "badge-pass"
    if s in ("PASS_WITH_WARNINGS", "WARN", "WARNING", "UNSIGNED"):
        return "badge-warn"
    if s in ("BLOCKED", "FAIL", "FALSE", "TAMPERED", "INVALID_SIGNATURE", "INVALID_CERTIFICATE"):
        return "badge-fail"
    return "badge-muted"


def _badge(status: Any) -> str:
    s = str(status)
    return f'<span class="badge {_badge_class(s)}">{_esc(s)}</span>'


def _kv_row(label: str, value: Any, mono: bool = False) -> str:
    cls = ' class="mono"' if mono else ""
    return f"<tr><th>{_esc(label)}</th><td{cls}>{_esc(value)}</td></tr>"


def render_passport_html(passport: dict[str, Any]) -> str:
    """Render a self-contained, offline-capable HTML Privacy Passport report."""
    ci = passport.get("certificate_identity", {})
    dp = passport.get("dataset_provenance", {})
    pa = passport.get("privacy_assessment", {})
    ia = passport.get("identity_assessment", {})
    cl = passport.get("clinical_integrity", {})
    sa = passport.get("security_assessment", {})
    rd = passport.get("release_decision", {})
    sig = passport.get("signature", {})

    rel_status = str(rd.get("status", "UNKNOWN"))
    sig_status = str(sig.get("status", "UNSIGNED"))
    cert_id = str(ci.get("certificate_id", "UNKNOWN"))

    gates = rd.get("gates", {})
    gate_rows = "".join(
        f"<tr><th>{_esc(k.replace('_', ' ').title())}</th><td>{_badge(v)}</td></tr>"
        for k, v in gates.items()
    )

    warnings = rd.get("warnings") or []
    blocking = rd.get("blocking_reasons") or []
    warn_items = "".join(f"<li>{_esc(w)}</li>" for w in warnings) or "<li>None</li>"
    block_items = "".join(f"<li>{_esc(b)}</li>" for b in blocking) or "<li>None</li>"

    pii = pa.get("pii_detection", {})
    res_leak = pa.get("residual_leakage_test", {})
    canary = pa.get("canary_test", {})
    ml = pa.get("multilingual_detection_coverage", {})
    qi = pa.get("quasi_identifier_risk", {})
    atk = pa.get("reidentification_attack_simulation", {})
    fhir = cl.get("fhir_validation", {})

    enc = sa.get("encryption_at_rest", {})
    tmp = sa.get("temporary_file_cleanup", {})
    log_s = sa.get("log_sanitisation", {})
    out_i = sa.get("output_integrity", {})
    pt = sa.get("path_traversal_protection", {})
    sec_c = sa.get("secret_configuration", {})

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>GuptKavach Privacy Passport — {_esc(cert_id)}</title>
<style>
  :root {{
    --bg: #070b14;
    --panel: #0e1628;
    --panel-alt: #131d33;
    --border: #1e2d4a;
    --text: #e2e8f0;
    --muted: #94a3b8;
    --accent: #3b82f6;
    --accent-soft: #60a5fa;
    --pass-bg: #052e1b;
    --pass-fg: #34d399;
    --warn-bg: #332206;
    --warn-fg: #fbbf24;
    --fail-bg: #3b0a14;
    --fail-fg: #f87171;
    --muted-bg: #1e293b;
    --muted-fg: #cbd5e1;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    padding: 28px 18px 48px;
    background: radial-gradient(circle at top right, #0f1b35 0%, var(--bg) 55%);
    color: var(--text);
    font-family: system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif;
    line-height: 1.5;
  }}
  .container {{ max-width: 1120px; margin: 0 auto; }}
  .header {{
    background: linear-gradient(135deg, #0c1426 0%, #111c34 100%);
    border: 1px solid var(--border);
    border-top: 3px solid var(--accent);
    border-radius: 10px;
    padding: 22px 24px;
    margin-bottom: 20px;
    display: flex;
    flex-wrap: wrap;
    justify-content: space-between;
    align-items: center;
    gap: 16px;
  }}
  .brand {{ font-size: 12px; letter-spacing: 0.14em; text-transform: uppercase; color: var(--accent-soft); font-weight: 700; }}
  h1 {{ margin: 4px 0 6px; font-size: 24px; font-weight: 700; color: #f8fafc; }}
  .sub {{ color: var(--muted); font-size: 13px; }}
  .status-cluster {{ display: flex; gap: 10px; flex-wrap: wrap; align-items: center; }}
  .badge {{
    display: inline-block;
    padding: 3px 10px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    border: 1px solid transparent;
  }}
  .badge-pass {{ background: var(--pass-bg); color: var(--pass-fg); border-color: #065f46; }}
  .badge-warn {{ background: var(--warn-bg); color: var(--warn-fg); border-color: #78350f; }}
  .badge-fail {{ background: var(--fail-bg); color: var(--fail-fg); border-color: #7f1d1d; }}
  .badge-muted {{ background: var(--muted-bg); color: var(--muted-fg); border-color: #334155; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(330px, 1fr)); gap: 16px; margin-bottom: 16px; }}
  .card {{
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 18px 20px;
  }}
  .card h2 {{
    margin: 0 0 12px;
    font-size: 14px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--accent-soft);
    border-bottom: 1px solid var(--border);
    padding-bottom: 8px;
  }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  th, td {{ padding: 6px 4px; text-align: left; border-bottom: 1px solid #16223b; vertical-align: top; }}
  th {{ color: var(--muted); font-weight: 500; width: 48%; }}
  td {{ color: #f1f5f9; font-weight: 500; word-break: break-word; }}
  .mono {{ font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 12px; }}
  .callout {{
    background: var(--panel-alt);
    border-left: 3px solid var(--accent);
    padding: 12px 14px;
    border-radius: 6px;
    font-size: 13px;
    margin-bottom: 12px;
  }}
  ul {{ margin: 6px 0 0 18px; padding: 0; font-size: 13px; color: var(--text); }}
  pre {{
    background: #060a12;
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 12px;
    overflow-x: auto;
    font-size: 12px;
    color: #93c5fd;
  }}
  .footer {{ margin-top: 20px; font-size: 12px; color: var(--muted); text-align: center; }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <div>
      <div class="brand">GuptKavach · Verifiable Release Certificate</div>
      <h1>Privacy Passport</h1>
      <div class="sub">Certificate ID: <span class="mono">{_esc(cert_id)}</span> · Schema: <span class="mono">{_esc(ci.get("schema_version", ""))}</span></div>
    </div>
    <div class="status-cluster">
      <span>Release: {_badge(rel_status)}</span>
      <span>Signature: {_badge(sig_status)}</span>
    </div>
  </div>

  <div class="card" style="margin-bottom: 16px;">
    <h2>G. Release Decision &amp; Policy Gate</h2>
    <div class="callout">{_esc(rd.get("explanation", ""))}</div>
    <div class="grid" style="margin-bottom: 0;">
      <div>
        <table>{gate_rows}</table>
      </div>
      <div>
        <div style="font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:0.06em;">Blocking Reasons</div>
        <ul>{block_items}</ul>
        <div style="font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:0.06em;margin-top:10px;">Warnings &amp; Limitations</div>
        <ul>{warn_items}</ul>
      </div>
    </div>
  </div>

  <div class="grid">
    <div class="card">
      <h2>A. Certificate Identity</h2>
      <table>
        {_kv_row("Certificate ID", ci.get("certificate_id"), mono=True)}
        {_kv_row("Schema Version", ci.get("schema_version"), mono=True)}
        {_kv_row("Created At (UTC)", ci.get("created_at"), mono=True)}
        {_kv_row("Expires At (UTC)", ci.get("expires_at"), mono=True)}
        {_kv_row("Engine Version", ci.get("engine_version"), mono=True)}
        {_kv_row("Policy Version", ci.get("policy_version"), mono=True)}
        <tr><th>Certificate Status</th><td>{_badge(ci.get("certificate_status", "UNSIGNED"))}</td></tr>
      </table>
    </div>

    <div class="card">
      <h2>B. Dataset Provenance</h2>
      <table>
        {_kv_row("Input Fingerprint (SHA-256)", dp.get("input_dataset_fingerprint"), mono=True)}
        {_kv_row("Output Root Hash (SHA-256)", dp.get("output_dataset_root_hash"), mono=True)}
        {_kv_row("Manifest File", dp.get("manifest_file"), mono=True)}
        {_kv_row("Input Files", dp.get("input_files_total"))}
        {_kv_row("Files Sanitised", dp.get("files_sanitised"))}
        {_kv_row("Files Quarantined", dp.get("files_quarantined"))}
        {_kv_row("Files Failed", dp.get("files_failed"))}
        {_kv_row("Records Processed", dp.get("records_processed"))}
        {_kv_row("Output Files / Bytes", f"{dp.get('output_files_count')} files / {dp.get('output_total_bytes')} B")}
      </table>
    </div>

    <div class="card">
      <h2>C. Privacy Assessment</h2>
      <table>
        <tr><th>PII Detection</th><td>{_badge(pii.get("status", "NOT_RUN"))} ({_esc(pii.get("direct_identifiers_detected"))} detected)</td></tr>
        {_kv_row("Generalizations / Suppressions", f"{pii.get('generalizations_applied')} / {pii.get('suppressions_applied')}")}
        <tr><th>Residual Leakage Test</th><td>{_badge(res_leak.get("status", "NOT_RUN"))} ({_esc(res_leak.get("leaks_detected"))})</td></tr>
        <tr><th>Canary Test</th><td>{_badge(canary.get("status", "NOT_RUN"))} ({_esc(canary.get("canaries_exposed"))} / {_esc(canary.get("canaries_total"))})</td></tr>
        {_kv_row("Scripts Supported", ", ".join(ml.get("scripts_supported", [])))}
        {_kv_row("Post-Mitigation Unique QIs", atk.get("post_uniquely_distinguishable"))}
        {_kv_row("Post-Mitigation Risk (C/H/M/L)", str(qi.get("post_categories", {})))}
      </table>
    </div>

    <div class="card">
      <h2>D. Identity Continuity Assessment</h2>
      <table>
        {_kv_row("Linked Records", ia.get("linked_records"))}
        {_kv_row("Unlinked Records", ia.get("unlinked_records"))}
        {_kv_row("Abstentions", ia.get("abstentions"))}
        {_kv_row("Identity Precision", ia.get("identity_precision"))}
        {_kv_row("Identity Recall", ia.get("identity_recall"))}
        {_kv_row("F0.5 Score", ia.get("f0_5_score"))}
        {_kv_row("False Merge Count", ia.get("false_merge_count"))}
        {_kv_row("Conflict Count", ia.get("conflict_count"))}
      </table>
    </div>

    <div class="card">
      <h2>E. Clinical Utility &amp; FHIR Integrity</h2>
      <table>
        {_kv_row("Expected Clinical Values", cl.get("expected_clinical_values"))}
        {_kv_row("Preserved Values", cl.get("preserved_values"))}
        {_kv_row("Modified Values", cl.get("modified_values"))}
        {_kv_row("Missing Values", cl.get("missing_values"))}
        {_kv_row("Preservation Rate", cl.get("clinical_preservation_rate"))}
        {_kv_row("Medication / Dosage / Lab", f"{cl.get('medication_integrity')} / {cl.get('dosage_integrity')} / {cl.get('laboratory_value_integrity')}")}
        <tr><th>FHIR R4 Validation</th><td>{_badge(fhir.get("status", "NOT_RUN"))} ({_esc(fhir.get("bundles_checked"))} bundles, {_esc(fhir.get("resources_checked"))} resources, passed={_esc(fhir.get("passed"))})</td></tr>
      </table>
    </div>

    <div class="card">
      <h2>F. Security &amp; Cryptographic Assessment</h2>
      <table>
        <tr><th>Encryption at Rest</th><td>{_badge(enc.get("status", "NOT_RUN"))} ({_esc(enc.get("quarantined_files_encrypted"))} vaulted)</td></tr>
        <tr><th>Temp File Cleanup</th><td>{_badge(tmp.get("status", "NOT_RUN"))}</td></tr>
        <tr><th>Log Sanitisation</th><td>{_badge(log_s.get("status", "NOT_RUN"))} (secret_exposed={_esc(log_s.get("secret_exposed"))})</td></tr>
        <tr><th>Output Integrity</th><td>{_badge(out_i.get("status", "NOT_RUN"))} ({_esc(out_i.get("algorithm"))})</td></tr>
        <tr><th>Path Traversal Protection</th><td>{_badge(pt.get("status", "NOT_RUN"))} (rejected={_esc(pt.get("rejected_paths"))})</td></tr>
        <tr><th>Secret Configuration</th><td>{_badge(sec_c.get("status", "WARNING"))} (RAKSHA_SECRET={_esc(sec_c.get("raksha_secret_configured"))})</td></tr>
        {_kv_row("Signature Algorithm / Key ID", f"{sig.get('algorithm')} / {sig.get('key_id')}", mono=True)}
      </table>
    </div>
  </div>

  <div class="card">
    <h2>Offline Verification Instructions</h2>
    <p style="font-size:13px;color:var(--muted);margin-top:0;">
      Verify cryptographic integrity and digital signature completely offline without trusting certificate claims alone:
    </p>
    <pre>python3 verify_passport.py --passport privacy_passport.json --output sanitized/</pre>
  </div>

  <div class="footer">
    Generated offline by GuptKavach Privacy Passport Engine ({_esc(ci.get("engine_version"))}) · Integrity verification proves tamper-evidence and policy evaluation, not formal mathematical anonymity.
  </div>
</div>
</body>
</html>
"""
