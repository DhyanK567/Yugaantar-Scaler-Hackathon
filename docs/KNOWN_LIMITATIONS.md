# GuptKavach — Known Limitations & Residual Risks

1. **Residual Quasi-Identifier Uniqueness**: Even after adaptive generalisation (`10y` age bands, PIN prefix/suppression, village/locality suppression), linked multi-record patients in small corpora can remain uniquely distinguishable under `cross_record_linkage` or `(10y_age_band, gender)` when `district` is retained for geographic utility.
2. **District Suppression Trade-off (`4847 / 4855`)**: Escalating `CRITICAL` combination-risk records to suppress `district` accounts for 8 suppressed location probes in `arogya_legacy_export.csv`.
3. **Standalone M9 Helpers**: `normalizer.py` and `evidence.py` are verified by `tests/multilingual/` but are not yet the primary runtime path inside `starter/main.py` (which uses `names.py` and `linking.py`).
4. **Offline Heuristic Scope**: Without LLMs or large NLP models (>50M params), completely unlabelled single-token first names that do not appear in structured fields, honorifics, or cluster context cannot be reliably distinguished from general prose without risking clinical over-redaction.
5. **Unstructured Clinical Notes & Dates**: Free-text dates without clear patient linkage fall back to record-level keys rather than cross-record patient date offsets.
