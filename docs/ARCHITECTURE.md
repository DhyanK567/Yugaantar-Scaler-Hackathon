# MediLocker Architecture

This document describes the implemented architecture of **MediLocker** (built on the GuptKavach / RAKSHA offline privacy engine).

---

## 1. High-Level System Architecture

```mermaid
flowchart LR
    subgraph Client["Local Browser (127.0.0.1:3001)"]
        UI["Next.js 16.4.6 / React 19.3.0 UI<br/>(Marketing + 12 Console Modules)"]
        APIClient["Central API Client<br/>frontend/src/lib/api.ts"]
        UI --> APIClient
    end

    subgraph WebAPI["FastAPI Backend (127.0.0.1:8000)"]
        MainAPI["backend/main.py<br/>CORS, RBAC, Endpoints"]
        Auth["backend/auth.py<br/>Sessions, SMTP OTP, Google OAuth, Offline Demo"]
        Pipeline["backend/pipeline.py<br/>Job Lifecycle & Passport Builder"]
        Adapter["backend/engine_adapter.py<br/>Subprocess CLI Bridge"]
        AuditMod["backend/audit.py<br/>Append-only Audit Logger"]
        MainAPI --> Auth
        MainAPI --> Pipeline
        MainAPI --> AuditMod
        Pipeline --> Adapter
        Pipeline --> AuditMod
    end

    subgraph Engine["Standalone Offline Privacy Engine (CPU-only)"]
        CLI["starter/main.py<br/>Two-Pass CLI"]
        Ingestion["Quarantine & Multi-Encoding<br/>quarantine.py, secure_fs.py"]
        PII["Multilingual PII & Names<br/>patterns.py, names.py, normalizer.py"]
        Linking["Identity Continuity<br/>evidence.py, linking.py"]
        Privacy["Sanitisation & QI Protection<br/>sanitizer.py, privacy.py, qi_classifier.py"]
        Validators["Risk, Attack & Clinical Validators<br/>risk_engine.py, attacker.py, clinical_validator.py"]
        CLI --> Ingestion --> PII --> Linking --> Privacy
        Pipeline -.->|"imports"| Validators
    end

    subgraph Persistence["Local Persistence (data/)"]
        DB[("SQLite (WAL + FKs)<br/>data/guptkavach.db")]
        FS["Local File Storage<br/>data/datasets/ & data/jobs/"]
    end

    APIClient -->|"HTTP + HttpOnly Cookie / Bearer"| MainAPI
    Adapter -->|"subprocess (HF_HUB_OFFLINE=1)"| CLI
    MainAPI <--> DB
    Auth <--> DB
    Pipeline <--> DB
    Pipeline <--> FS
    CLI -->|"sanitized/, report.json, records.jsonl"| FS
```

---

## 2. Dataset Processing Lifecycle

```mermaid
flowchart TD
    A["1. Dataset Upload<br/>POST /api/datasets or /api/jobs"] --> B["2. Validation<br/>Extension, non-empty, SHA-256, org RBAC"]
    B --> C["3. Processing Job Created<br/>jobs + job_events (CREATED -> VALIDATING)"]
    C --> D["4. Offline Engine Execution<br/>starter/main.py subprocess (PROCESSING)"]
    D --> E["5. Quarantine Gate & Ingestion<br/>quarantine.py isolates PDF/PNG/corrupt JSON"]
    E --> F["6. Multilingual PII Detection<br/>patterns.py, names.py (English/Devanagari/Hinglish)"]
    F --> G["7. Clinical Preservation<br/>Medical guards + clinical_validator.py (FHIR R4)"]
    G --> H["8. Identity Resolution & Pseudonymisation<br/>linking.py + HMAC-SHA256 PSN-XXXXXX"]
    H --> I["9. Privacy & Risk Analysis<br/>Canary scan + 7-vector simulate_attacks()"]
    I --> J{"10. Release Decision"}
    J -->|"Canaries leaked = 0, no warnings"| K1["APPROVED / COMPLETED"]
    J -->|"Quarantined files or missing clinical"| K2["APPROVED_WITH_WARNINGS / QUARANTINED"]
    J -->|"Canary leaked or engine failure"| K3["BLOCKED / FAILED"]
    K1 --> L["11. Privacy Passport (UNSIGNED SHA-256 Manifest)<br/>+ Append-only Audit Event"]
    K2 --> L
    K3 --> L
```

---

## 3. Component Summary

| Layer | Implementation Files | Responsibility |
|---|---|---|
| **Frontend Shell & Pages** | `frontend/src/components/layout/`, `frontend/src/components/dashboard/`, `frontend/src/app/` | Marketing site, Login/OTP/OAuth callback, 7-section Dashboard, 12 console modules. |
| **Desktop / Local Launcher** | `launcher/medilocker_launcher.py`, `Start-MediLocker.bat` | Single-instance lockfile, port checks, SQLite init, loopback `127.0.0.1` startup, WAL checkpoint on exit. |
| **Backend API & Auth** | `backend/main.py`, `backend/auth.py`, `backend/audit.py` | RBAC (`PLATFORM_ADMIN`, `ORG_ADMIN`, `PRIVACY_OFFICER`, `RESEARCHER`, `AUDITOR`), SMTP Email OTP, Google OAuth 2.0/OIDC, Offline Demo Mode. |
| **Pipeline & Engine Bridge** | `backend/pipeline.py`, `backend/engine_adapter.py` | Orchestrates `starter/main.py`, canary scanning, FHIR R4 clinical validation, `simulate_attacks`, and Privacy Passport generation. |
| **Offline Privacy Engine** | `starter/main.py`, `starter/raksha_engine/*.py` | Standalone Python stdlib-only two-pass engine; executes independently of FastAPI, Next.js, and network access. |
| **Database** | `backend/database.py` | SQLite (`data/guptkavach.db`) with `PRAGMA foreign_keys = ON` and `WAL` mode across 16 tables. |
| **PDF Utility (Standalone)** | `generate_pdf.py` | Standalone ReportLab generator producing the 2-page `GuptKavach_Project_Brief.pdf`. |
