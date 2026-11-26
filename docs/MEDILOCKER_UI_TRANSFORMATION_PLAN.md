# MediLocker UI Transformation Plan

## 1. Overview
This document outlines the transformation of the GuptKavach frontend console into **MediLocker** — a healthcare data privacy and secure research collaboration infrastructure platform.

## 2. Existing Architecture
- **Frontend:** Next.js 16.4.6 (App Router, Turbopack), React 19.3.0, TypeScript 5.9.3, Tailwind CSS 4.3.3, `lucide-react` 1.80.0.
- **Backend:** FastAPI (`backend/main.py`) with SQLite (`backend/database.py`) and subprocess engine adapter (`backend/engine_adapter.py`) invoking `starter/main.py`.
- **Core Privacy Engine:** `starter/raksha_engine/` — deterministic, offline, CPU-only privacy engine (Milestones 8, 11, 13, 14).

## 3. Design System
- **Palette:** Strictly monochrome Swiss-inspired system:
  - Primary background: `#F2F2F2`
  - Surface / Cards: `#FFFFFF`
  - Primary text / dark surface: `#050505`
  - Secondary surface: `#E6E6E6`
  - Borders: `#DCDCDC`
  - Muted text: `#777777`
- **Typography:** `"SF Pro Display", -apple-system, BlinkMacSystemFont, "Inter", "Segoe UI", system-ui, sans-serif`
- **Logo:** `frontend/public/medilocker-logo.jpg` (black circle with white ML monogram and padlock).

## 4. Route & API Integration Map
| Route | Backend Endpoint(s) | Purpose |
|---|---|---|
| `/` | — | Marketing homepage with hero, stats, console preview, capabilities |
| `/faq` | — | Interactive FAQ accordion |
| `/pricing` | — | 3-tier transparent pricing (Starter, Pro, Enterprise) |
| `/login`, `/register`, `/forgot-password` | Frontend session gate | Authentication UI (backend auth integration-ready) |
| `/dashboard` | `GET /api/dashboard` | Live metrics, recent jobs, audit events |
| `/dashboard/datasets` | `GET /api/datasets`, `POST /api/jobs`, `GET /api/jobs/{id}`, `GET /api/jobs/{id}/download` | Dataset upload, job polling, sanitised output download |
| `/dashboard/organisations` | `GET /api/organisations` | Connected hospitals, labs, research institutions |
| `/dashboard/privacy-engine` | `GET /api/dashboard`, `GET /api/settings` | Pipeline stages, deterministic policy inspection |
| `/dashboard/privacy-intelligence` | `GET /api/privacy-intelligence`, `GET /api/threat-lab` | PII breakdown, language distribution, risk distribution |
| `/dashboard/attack-simulator` | `GET /api/threat-lab` | Adversarial attack simulation results & mitigations |
| `/dashboard/identity-continuity` | `GET /api/identity-graph` | Cross-hospital patient identity graph & linkage stats |
| `/dashboard/clinical-integrity` | `GET /api/dashboard` | Clinical value preservation & FHIR R4 integrity metrics |
| `/dashboard/privacy-passports` | `GET /api/dashboard`, `GET /api/jobs/{id}/download` | Verifiable Privacy Passport manifests |
| `/dashboard/research-network` | `GET /api/research/requests`, `POST /api/research/requests`, `POST /api/research/requests/{id}/approve\|reject` | Research collaboration & data access approvals |
| `/dashboard/audit` | `GET /api/audit` | Immutable governance & privacy audit log |
| `/dashboard/settings` | `GET /api/settings`, `POST /api/settings` | Engine configuration & policy thresholds |

## 5. Non-Negotiable Constraints Preserved
- `starter/main.py`, `validate_output.py`, `check_dev.py`, and `check_submission.py` remain untouched.
- Zero LLMs, hosted AI, or cloud inference in the privacy engine.
- No hardcoded fake metrics in place of API data — clean empty/unavailable states are shown when the backend is offline or empty.
- No raw PII is ever displayed or logged in the frontend.
