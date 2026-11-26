"""MediLocker Offline PDF Reporting & Evidence Generation Subsystem."""
from .security import PdfSecurityError
from .service import (
    PdfGenerationError,
    generate_attack_simulation_pdf,
    generate_audit_trail_pdf,
    generate_clinical_integrity_pdf,
    generate_privacy_intelligence_pdf,
    generate_privacy_passport_pdf,
)

__all__ = [
    "PdfGenerationError",
    "PdfSecurityError",
    "generate_privacy_passport_pdf",
    "generate_privacy_intelligence_pdf",
    "generate_attack_simulation_pdf",
    "generate_clinical_integrity_pdf",
    "generate_audit_trail_pdf",
]
