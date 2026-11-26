"""Append-only Audit Event Logger for MediLocker.
Never logs secrets, OTPs, passwords, or raw PII.
"""
from __future__ import annotations

import time
from typing import Optional

from .database import get_db


def record_audit_event(
    *,
    action: str,
    resource_type: str,
    outcome: str,
    actor_id: Optional[str] = None,
    actor_email: Optional[str] = None,
    actor_role: Optional[str] = None,
    organisation_id: Optional[str] = None,
    resource_id: Optional[str] = None,
    details: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> None:
    """Append an immutable audit event to audit_events."""
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO audit_events (
                timestamp, actor_id, actor_email, actor_role, organisation_id,
                action, resource_type, resource_id, outcome, details, ip_address
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                time.time(),
                actor_id,
                actor_email,
                actor_role,
                organisation_id,
                action,
                resource_type,
                resource_id,
                outcome,
                details,
                ip_address,
            ),
        )
