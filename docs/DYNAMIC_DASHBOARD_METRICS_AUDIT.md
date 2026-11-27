# MediLocker — Dynamic Dashboard Metrics & Data Integrity Audit

## 1. Executive Summary
Inspection of the screenshot and codebase identified two root causes of static or mixed KPI metrics:
1. **Hardcoded Landing KPI Cards (`frontend/src/app/page.tsx`, lines 4–37)**:
   - `TRUST_METRICS` hardcodes static strings directly in the React component:
     - `"0/4"` — `Canary leaks` — `"dev/input · 200 files"`
     - `"1.00"` — `Identity precision` — `"823 records · 0 false merges"`
     - `"99.8%"` — `Clinical data preserved` — `"4,449 / 4,457 values"` (stale M16.2 denominator)
     - `"100%"` — `Offline, CPU-only` — `"Zero LLMs · Zero cloud calls"`
2. **Mixed-Job Aggregation & Missing Job Selection in Dashboard (`backend/main.py` & `frontend/src/app/dashboard/page.tsx`)**:
   - `_compute_dashboard_payload()` in `backend/main.py` aggregates `files_processed`, `clinical_reports`, and `privacy_assessments` globally across all jobs without excluding failed/cancelled jobs or scoping to a single selected job.
   - `id_metric` mixes `latest_id["precision"]` (from one job) with `sum(false_merges)` (across all jobs).
   - No `GET /api/jobs/{job_id}/dashboard-metrics` or job-scoped selector (`Viewing results for: [Latest completed job ▼]`) exists on `/dashboard`.
   - No structured **Execution Compliance** telemetry (`mode`, `device`, `llm_dependency`, `network_calls`, `verification_status`, `scope`) is exposed by the backend.

---

## 2. Original Source vs. Authoritative Backend Source

| Screenshot Card | Original Source | Authoritative Backend Source | Remediation |
|---|---|---|---|
| `0/4` Canary leaks | Hardcoded `TRUST_METRICS[0]` in `frontend/src/app/page.tsx:5-12` | `privacy_assessments` (`canary_planted`, `canary_leaks`, `canary_status`) scoped to selected completed `job_id` | Return `NOT_TESTED` when `canary_planted == 0` or `canary_status == "NOT_RUN"`; never assume `/4`. |
| `1.00` Identity precision | Hardcoded `TRUST_METRICS[1]` in `frontend/src/app/page.tsx:14-20` | `identity_clusters` (`precision`, `false_merges`, `total_patients`, `graph_json`) scoped to selected `job_id` | Compute `TP / (TP + FP)` where available; return `NOT_MEASURED` when denominator is `0` or unmeasured. |
| `99.8%` Clinical data preserved (`4,449 / 4,457`) | Hardcoded `TRUST_METRICS[2]` in `frontend/src/app/page.tsx:22-28` | `clinical_reports` (`expected_values`, `preserved_values`, `modified_values`, `missing_values`) scoped to selected `job_id` | Exact ratio `(preserved / expected) * 100` (e.g. `99.82%`); never count modified as preserved; `NOT_MEASURED` if `expected == 0`. |
| `100%` Offline, CPU-only | Hardcoded `TRUST_METRICS[3]` in `frontend/src/app/page.tsx:30-36` | Runtime & repository compliance check (`OFFLINE`, `CPU`, `LLM=NONE`, `REPOSITORY_AUDIT`) | Present verified runtime properties & scope (`Engine compliance · Repository audit`) rather than a fake per-dataset `100%`. |

---

## 3. Target Architecture
- **New Consolidated Endpoint**: `GET /api/jobs/{job_id}/dashboard-metrics` (plus `GET /api/dashboard/metrics-summary?scope=latest|aggregate|<job_id>`) returning strict job-isolated or mathematically valid aggregate metrics with explicit `status` (`TESTED`, `NOT_TESTED`, `MEASURED`, `NOT_MEASURED`, `FAILED`) and nullability.
- **Public Landing (`frontend/src/app/page.tsx`)**: Remove hardcoded `4,449 / 4,457`, `0/4`, `1.00`, and `100%` benchmark claims; render verified runtime/system compliance from `/api/system/compliance` (or explicit `Sign in to view dataset metrics` / `Not measured` states) with zero fabricated numbers.
- **Dashboard (`frontend/src/app/dashboard/page.tsx`)**: Add `Viewing results for: [Latest completed job ▼]` selector (Latest completed job, All completed datasets aggregate, or any historical completed job) updating the 4-card Privacy Performance Overview and preserving MediLocker's monochrome design language.
