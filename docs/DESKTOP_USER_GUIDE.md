# MediLocker Windows Desktop User Guide

## 1. First Launch
1. Launch **MediLocker** from the Start Menu or Desktop shortcut.
2. On `/login`, click **Continue in Offline Demo Mode** (no internet, SMTP, or Google account required).

## 2. Core Privacy Workflow
1. **Select Organisation:** Use the sidebar organisation selector (`Metro General Hospital`, `Apex Care Medical Centre`, etc.).
2. **Upload Dataset:** Go to **02. Datasets**, select target organisation, and upload synthetic `.csv`, `.tsv`, `.json`, `.jsonl`, or `.txt` files.
3. **Monitor Processing:** Live job stages (`VALIDATING` → `PROCESSING` → `PRIVACY_ANALYSIS` → `CLINICAL_VALIDATION` → `SECURITY_VALIDATION` → `COMPLETED`) update automatically.
4. **Inspect Evidence:**
   - **01. Overview:** Release readiness, 6 metric cards, 6-stage workflow, Recent Jobs, Audit Events.
   - **04. Privacy Intelligence & 05. Attack Simulator:** PII detection, canary containment, and 7-vector attack simulation.
   - **07. Identity Continuity & 08. Clinical Integrity:** Pseudonymous `PSN-XXXXXX` clusters and exact preserved/expected clinical counts.
   - **09. Privacy Passports:** Verify SHA-256 manifest integrity (`UNSIGNED`) and download JSON/HTML.
   - **12. Settings:** View **Offline System Diagnostics** and download the **Operational PDF** report.
