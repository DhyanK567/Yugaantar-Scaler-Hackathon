"""Authentication, SMTP Email OTP, Google OAuth 2.0/OIDC, Sessions & RBAC for MediLocker.
Completely decoupled from the offline privacy engine (starter/main.py).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import re
import secrets
import smtplib
import time
import urllib.parse
from collections import defaultdict
from email.message import EmailMessage
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

import requests as http_requests
from fastapi import Cookie, Depends, Header, HTTPException, Request, Response, status
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

from .audit import record_audit_event
from .database import get_db

# Ephemeral fallback key for dev/testing if MEDILOCKER_AUTH_SECRET is not set
_EPHEMERAL_AUTH_SECRET = secrets.token_bytes(32)


def _get_auth_secret() -> bytes:
    env_secret = os.environ.get("MEDILOCKER_AUTH_SECRET")
    if env_secret:
        return env_secret.encode("utf-8")
    return _EPHEMERAL_AUTH_SECRET


SESSION_COOKIE_NAME = "medilocker_session"
SESSION_TTL_SECONDS = int(os.environ.get("MEDILOCKER_SESSION_TTL", "86400"))
OTP_EXPIRY_SECONDS = int(os.environ.get("OTP_EXPIRY_SECONDS", "300"))
OTP_RESEND_COOLDOWN_SECONDS = int(os.environ.get("OTP_RESEND_COOLDOWN_SECONDS", "60"))
OTP_MAX_ATTEMPTS = 5

EMAIL_RE = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")

# Role hierarchy & permissions
ROLE_PLATFORM_ADMIN = "PLATFORM_ADMIN"
ROLE_ORG_ADMIN = "ORG_ADMIN"
ROLE_PRIVACY_OFFICER = "PRIVACY_OFFICER"
ROLE_RESEARCHER = "RESEARCHER"
ROLE_AUDITOR = "AUDITOR"

ALL_ROLES = {
    ROLE_PLATFORM_ADMIN,
    ROLE_ORG_ADMIN,
    ROLE_PRIVACY_OFFICER,
    ROLE_RESEARCHER,
    ROLE_AUDITOR,
}

# Simple in-memory rate limiter (key -> list of timestamps)
_RATE_BUCKETS: Dict[str, List[float]] = defaultdict(list)


def check_rate_limit(key: str, limit: int, window_seconds: int) -> bool:
    now = time.time()
    bucket = _RATE_BUCKETS[key]
    _RATE_BUCKETS[key] = [t for t in bucket if now - t < window_seconds]
    if len(_RATE_BUCKETS[key]) >= limit:
        return False
    _RATE_BUCKETS[key].append(now)
    return True


def reset_rate_limits() -> None:
    _RATE_BUCKETS.clear()


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _hash_otp(email: str, purpose: str, otp: str) -> str:
    msg = f"{email.lower()}:{purpose}:{otp}".encode("utf-8")
    return hmac.new(_get_auth_secret(), msg, hashlib.sha256).hexdigest()


# ==============================================================================
# SMTP Email Service
# ==============================================================================


def get_smtp_config() -> Dict[str, Any]:
    host = os.environ.get("SMTP_HOST", "").strip()
    port = int(os.environ.get("SMTP_PORT", "587") or "587")
    username = os.environ.get("SMTP_USERNAME", "").strip()
    password = os.environ.get("SMTP_PASSWORD", "").strip()
    from_email = os.environ.get("SMTP_FROM_EMAIL", "").strip() or username
    from_name = os.environ.get("SMTP_FROM_NAME", "MediLocker").strip()
    use_tls = os.environ.get("SMTP_USE_TLS", "true").lower() != "false"
    configured = bool(host and from_email)
    return {
        "configured": configured,
        "host": host,
        "port": port,
        "username": username,
        "password": password,
        "from_email": from_email,
        "from_name": from_name,
        "use_tls": use_tls,
    }


def send_otp_email(to_email: str, otp_code: str, expiry_minutes: int = 5) -> None:
    """Send OTP via configured SMTP server with MediLocker monochrome HTML + plain-text body.
    Raises RuntimeError if unconfigured or delivery fails.
    """
    cfg = get_smtp_config()
    if not cfg["configured"]:
        raise RuntimeError("SMTP_NOT_CONFIGURED")

    msg = EmailMessage()
    msg["Subject"] = f"Use {otp_code} to sign in to MediLocker"
    msg["From"] = f"{cfg['from_name']} <{cfg['from_email']}>"
    msg["To"] = to_email

    # Plain-text fallback
    msg.set_content(
        f"Use {otp_code} to sign in to MediLocker.\n\n"
        f"Your verification code is: {otp_code}\n"
        f"This code expires in {expiry_minutes} minutes and can only be used once.\n\n"
        f"If you did not request this code, you can safely ignore this email."
    )

    # Monochrome MediLocker HTML template with 6 individual digit cells
    digit_cells = "".join(
        f'<td style="width:42px;height:48px;background:#F2F2F2;border:1.5px solid #DCDCDC;'
        f'border-radius:8px;text-align:center;vertical-align:middle;font-size:22px;'
        f'font-weight:700;color:#050505;font-family:\'SF Pro Display\',-apple-system,Inter,Arial,sans-serif;">'
        f"{d}</td>"
        for d in otp_code
    )
    html_body = f"""<!doctype html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:32px 16px;background:#F2F2F2;font-family:'SF Pro Display',-apple-system,BlinkMacSystemFont,'Inter',Arial,sans-serif;color:#050505;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:480px;margin:0 auto;background:#FFFFFF;border:1.5px solid #DCDCDC;border-radius:12px;overflow:hidden;">
    <tr>
      <td style="background:#050505;padding:22px 28px;">
        <span style="font-size:18px;font-weight:700;color:#FFFFFF;letter-spacing:-0.4px;">MediLocker</span>
        <span style="display:block;font-size:11.5px;color:#AAAAAA;margin-top:3px;">Secure. Private. Clinically Usable.</span>
      </td>
    </tr>
    <tr>
      <td style="padding:30px 28px 26px;">
        <div style="font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:0.8px;color:#777777;margin-bottom:8px;">
          Verification Code
        </div>
        <h1 style="margin:0 0 10px;font-size:20px;font-weight:700;color:#050505;letter-spacing:-0.4px;">
          Sign in to your MediLocker account
        </h1>
        <p style="margin:0 0 22px;font-size:14px;line-height:1.55;color:#555555;">
          Enter the 6-digit verification code below to complete your sign-in. This code expires in <strong>{expiry_minutes} minutes</strong> and can only be used once.
        </p>
        <table role="presentation" cellspacing="8" cellpadding="0" style="margin:0 auto 22px;">
          <tr>{digit_cells}</tr>
        </table>
        <div style="background:#F2F2F2;border:1px solid #E6E6E6;border-radius:8px;padding:12px 14px;font-size:12px;line-height:1.5;color:#555555;">
          <strong>Security Notice:</strong> Never share this code with anyone. MediLocker will never ask for your verification code by phone or message.
        </div>
      </td>
    </tr>
    <tr>
      <td style="padding:14px 28px;border-top:1px solid #EEEEEE;font-size:11.5px;color:#777777;">
        If you did not request this verification code, you can safely ignore this email.
      </td>
    </tr>
  </table>
</body>
</html>"""

    msg.add_alternative(html_body, subtype="html")

    if cfg["port"] == 465:
        with smtplib.SMTP_SSL(cfg["host"], cfg["port"], timeout=15) as server:
            if cfg["username"] and cfg["password"]:
                server.login(cfg["username"], cfg["password"])
            server.send_message(msg)
    else:
        with smtplib.SMTP(cfg["host"], cfg["port"], timeout=15) as server:
            if cfg["use_tls"]:
                server.starttls()
            if cfg["username"] and cfg["password"]:
                server.login(cfg["username"], cfg["password"])
            server.send_message(msg)


def is_offline_mode_enabled() -> bool:
    """Return True when explicitly launched in offline-first local mode."""
    return os.environ.get("MEDILOCKER_OFFLINE_MODE", "false").lower() == "true"


def offline_demo_login(
    email: Optional[str], ip_address: Optional[str], user_agent: Optional[str]
) -> Tuple[str, Dict[str, Any]]:
    """Local offline-first demo access (requires MEDILOCKER_OFFLINE_MODE=true)."""
    if not is_offline_mode_enabled():
        raise HTTPException(
            status_code=403,
            detail="Offline demo mode is disabled. Enable MEDILOCKER_OFFLINE_MODE=true for local offline launch.",
        )
    target_email = (email or "privacy@metrogeneral.org").strip().lower()
    if not EMAIL_RE.match(target_email):
        raise HTTPException(status_code=400, detail="Invalid email format")

    now = time.time()
    with get_db() as conn:
        user_row = conn.execute(
            "SELECT id, status FROM users WHERE lower(email) = ?", (target_email,)
        ).fetchone()
        if user_row and user_row["status"] != "ACTIVE":
            raise HTTPException(status_code=401, detail="Account is not active")
        if user_row:
            user_id = user_row["id"]
        else:
            user_id = f"usr-{secrets.token_hex(8)}"
            conn.execute(
                "INSERT INTO users (id, email, full_name, status, platform_role, created_at) VALUES (?, ?, ?, 'ACTIVE', 'USER', ?)",
                (user_id, target_email, target_email.split("@")[0], now),
            )
            first_org = conn.execute(
                "SELECT id FROM organisations ORDER BY joined_at ASC LIMIT 1"
            ).fetchone()
            if first_org:
                conn.execute(
                    "INSERT INTO memberships (id, user_id, organisation_id, role, created_at) VALUES (?, ?, ?, ?, ?)",
                    (f"mem-{secrets.token_hex(8)}", user_id, first_org["id"], ROLE_PRIVACY_OFFICER, now),
                )

    ctx = load_user_context(user_id)
    if not ctx:
        raise HTTPException(status_code=401, detail="Account is not active")

    raw_token, sess_meta = create_session(
        user_id=user_id,
        active_org_id=ctx["active_org_id"],
        ip_address=ip_address,
        user_agent=user_agent,
    )
    ctx["session_id"] = sess_meta["session_id"]

    record_audit_event(
        action="LOGIN_OFFLINE_DEMO",
        resource_type="session",
        resource_id=sess_meta["session_id"],
        outcome="SUCCESS",
        actor_id=user_id,
        actor_email=ctx["email"],
        actor_role=ctx["active_role"],
        organisation_id=ctx["active_org_id"],
        details="Authenticated via Offline Local Demo Mode (no external network services)",
        ip_address=ip_address,
    )
    return raw_token, ctx


def is_dev_email_login_enabled() -> bool:
    """Allow direct email sign-in only in local development when SMTP is not configured."""
    env = os.environ.get("MEDILOCKER_ENV", "development").lower()
    if env == "production":
        return False
    return not get_smtp_config()["configured"]


def dev_email_login(
    email: str, ip_address: Optional[str], user_agent: Optional[str]
) -> Tuple[str, Dict[str, Any]]:
    if not is_dev_email_login_enabled():
        raise HTTPException(
            status_code=403,
            detail="Direct email sign-in is disabled when SMTP is configured or in production.",
        )
    normalized = email.strip().lower()
    if not EMAIL_RE.match(normalized):
        raise HTTPException(status_code=400, detail="Invalid email format")

    now = time.time()
    with get_db() as conn:
        user_row = conn.execute(
            "SELECT id, status FROM users WHERE lower(email) = ?", (normalized,)
        ).fetchone()
        if user_row and user_row["status"] != "ACTIVE":
            raise HTTPException(status_code=401, detail="Account is not active")
        if user_row:
            user_id = user_row["id"]
        else:
            user_id = f"usr-{secrets.token_hex(8)}"
            display_name = normalized.split("@")[0]
            conn.execute(
                """
                INSERT INTO users (id, email, full_name, status, platform_role, created_at)
                VALUES (?, ?, ?, 'ACTIVE', 'USER', ?)
                """,
                (user_id, normalized, display_name, now),
            )
            first_org = conn.execute(
                "SELECT id FROM organisations ORDER BY joined_at ASC LIMIT 1"
            ).fetchone()
            if first_org:
                conn.execute(
                    """
                    INSERT INTO memberships (id, user_id, organisation_id, role, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (f"mem-{secrets.token_hex(8)}", user_id, first_org["id"], ROLE_PRIVACY_OFFICER, now),
                )

    ctx = load_user_context(user_id)
    if not ctx:
        raise HTTPException(status_code=401, detail="Account is not active")

    raw_token, sess_meta = create_session(
        user_id=user_id,
        active_org_id=ctx["active_org_id"],
        ip_address=ip_address,
        user_agent=user_agent,
    )
    ctx["session_id"] = sess_meta["session_id"]

    record_audit_event(
        action="LOGIN_DEV_EMAIL",
        resource_type="session",
        resource_id=sess_meta["session_id"],
        outcome="SUCCESS",
        actor_id=user_id,
        actor_email=ctx["email"],
        actor_role=ctx["active_role"],
        organisation_id=ctx["active_org_id"],
        details="Authenticated via local dev email sign-in (SMTP unconfigured)",
        ip_address=ip_address,
    )
    return raw_token, ctx


# ==============================================================================
# Google OAuth Configuration
# ==============================================================================


def get_google_config() -> Dict[str, Any]:
    client_id = os.environ.get("GOOGLE_CLIENT_ID", "").strip()
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET", "").strip()
    redirect_uri = os.environ.get(
        "GOOGLE_REDIRECT_URI", "http://localhost:3001/auth/google/callback"
    ).strip()
    configured = bool(client_id and client_secret and redirect_uri)
    return {
        "configured": configured,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
    }


# ==============================================================================
# Session Management
# ==============================================================================


def create_session(
    user_id: str,
    active_org_id: Optional[str],
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Tuple[str, Dict[str, Any]]:
    raw_token = secrets.token_urlsafe(32)
    token_hash = _hash_token(raw_token)
    session_id = f"sess-{secrets.token_hex(12)}"
    now = time.time()
    expires_at = now + SESSION_TTL_SECONDS

    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO sessions (id, token_hash, user_id, active_org_id, expires_at, created_at, ip_address, user_agent)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (session_id, token_hash, user_id, active_org_id, expires_at, now, ip_address, user_agent),
        )
        conn.execute("UPDATE users SET last_login_at = ? WHERE id = ?", (now, user_id))

    return raw_token, {
        "session_id": session_id,
        "expires_at": expires_at,
        "active_org_id": active_org_id,
    }


def revoke_session_by_token(raw_token: str) -> None:
    token_hash = _hash_token(raw_token)
    with get_db() as conn:
        conn.execute(
            "UPDATE sessions SET revoked_at = ? WHERE token_hash = ? AND revoked_at IS NULL",
            (time.time(), token_hash),
        )


def set_session_cookie(response: Response, raw_token: str) -> None:
    is_prod = os.environ.get("MEDILOCKER_ENV", "development").lower() == "production"
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=raw_token,
        httponly=True,
        samesite="lax",
        secure=is_prod,
        max_age=SESSION_TTL_SECONDS,
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(key=SESSION_COOKIE_NAME, path="/")


def load_user_context(user_id: str, active_org_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    with get_db() as conn:
        user_row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if not user_row or user_row["status"] != "ACTIVE":
            return None
        memberships = [
            dict(r)
            for r in conn.execute(
                """
                SELECT m.id, m.organisation_id, m.role, o.name as organisation_name, o.org_type
                FROM memberships m
                JOIN organisations o ON o.id = m.organisation_id
                WHERE m.user_id = ?
                ORDER BY m.created_at ASC
                """,
                (user_id,),
            ).fetchall()
        ]
        oauth_links = [
            dict(r)
            for r in conn.execute(
                "SELECT provider, email, email_verified, created_at FROM oauth_identities WHERE user_id = ?",
                (user_id,),
            ).fetchall()
        ]

    resolved_org_id = active_org_id
    if not resolved_org_id and memberships:
        resolved_org_id = memberships[0]["organisation_id"]

    active_role = None
    if user_row["platform_role"] == ROLE_PLATFORM_ADMIN:
        active_role = ROLE_PLATFORM_ADMIN
    else:
        for m in memberships:
            if m["organisation_id"] == resolved_org_id:
                active_role = m["role"]
                break

    return {
        "id": user_row["id"],
        "email": user_row["email"],
        "full_name": user_row["full_name"],
        "platform_role": user_row["platform_role"],
        "active_org_id": resolved_org_id,
        "active_role": active_role,
        "memberships": memberships,
        "oauth_providers": oauth_links,
    }


def _extract_token(
    cookie_token: Optional[str], authorization: Optional[str]
) -> Optional[str]:
    if authorization and authorization.lower().startswith("bearer "):
        return authorization.split(" ", 1)[1].strip()
    if cookie_token:
        return cookie_token
    return None


def get_current_user_optional(
    request: Request,
    medilocker_session: Optional[str] = Cookie(default=None),
    authorization: Optional[str] = Header(default=None),
) -> Optional[Dict[str, Any]]:
    raw_token = _extract_token(medilocker_session, authorization)
    if not raw_token:
        return None
    token_hash = _hash_token(raw_token)
    now = time.time()
    with get_db() as conn:
        sess = conn.execute(
            "SELECT * FROM sessions WHERE token_hash = ?", (token_hash,)
        ).fetchone()
        if not sess:
            return None
        if sess["revoked_at"] is not None or sess["expires_at"] <= now:
            return None
        ctx = load_user_context(sess["user_id"], sess["active_org_id"])
        if ctx:
            ctx["session_id"] = sess["id"]
            ctx["raw_token"] = raw_token
        return ctx


def require_user(
    user: Optional[Dict[str, Any]] = Depends(get_current_user_optional),
) -> Dict[str, Any]:
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    return user


def user_has_org_access(user: Dict[str, Any], organisation_id: str) -> bool:
    if user.get("platform_role") == ROLE_PLATFORM_ADMIN:
        return True
    return any(m["organisation_id"] == organisation_id for m in user.get("memberships", []))


def get_user_org_role(user: Dict[str, Any], organisation_id: Optional[str]) -> Optional[str]:
    if user.get("platform_role") == ROLE_PLATFORM_ADMIN:
        return ROLE_PLATFORM_ADMIN
    if not organisation_id:
        return user.get("active_role")
    for m in user.get("memberships", []):
        if m["organisation_id"] == organisation_id:
            return m["role"]
    return None


def require_org_access(
    user: Dict[str, Any],
    organisation_id: str,
    allowed_roles: Optional[Iterable[str]] = None,
) -> str:
    if not user_has_org_access(user, organisation_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied for this organisation",
        )
    role = get_user_org_role(user, organisation_id)
    if allowed_roles is not None and role not in set(allowed_roles):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient role permissions",
        )
    return role or ""


def require_roles(allowed_roles: Iterable[str]) -> Callable:
    allowed = set(allowed_roles)

    def _dep(user: Dict[str, Any] = Depends(require_user)) -> Dict[str, Any]:
        if user.get("platform_role") == ROLE_PLATFORM_ADMIN:
            return user
        role = user.get("active_role")
        if role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient role permissions",
            )
        return user

    return _dep


# ==============================================================================
# Email OTP Logic
# ==============================================================================


def request_email_otp(email: str, purpose: str, ip_address: Optional[str]) -> Dict[str, Any]:
    normalized = email.strip().lower()
    if not EMAIL_RE.match(normalized):
        raise HTTPException(status_code=400, detail="Invalid email format")

    # Rate limit by IP and email
    if not check_rate_limit(f"otp_req_ip:{ip_address or 'unknown'}", limit=10, window_seconds=300):
        raise HTTPException(status_code=429, detail="Too many requests. Please wait before trying again.")
    if not check_rate_limit(f"otp_req_email:{normalized}", limit=5, window_seconds=300):
        raise HTTPException(status_code=429, detail="Too many verification requests for this email.")

    cfg = get_smtp_config()
    if not cfg["configured"]:
        record_audit_event(
            action="OTP_REQUEST",
            resource_type="auth",
            outcome="FAILED",
            actor_email=normalized,
            details="SMTP not configured",
            ip_address=ip_address,
        )
        raise HTTPException(
            status_code=503,
            detail="Email OTP service is not configured on the server.",
        )

    now = time.time()
    generic_response = {
        "status": "ok",
        "message": "If this account is eligible, a verification code will be sent.",
    }

    with get_db() as conn:
        user_row = conn.execute(
            "SELECT id, status FROM users WHERE lower(email) = ?", (normalized,)
        ).fetchone()

        if user_row and user_row["status"] != "ACTIVE":
            # Anti-enumeration: do not reveal that account is suspended/disabled
            record_audit_event(
                action="OTP_REQUEST",
                resource_type="auth",
                outcome="IGNORED_INELIGIBLE",
                details="OTP requested for inactive account",
                ip_address=ip_address,
            )
            return generic_response

        # Resend cooldown check
        recent = conn.execute(
            """
            SELECT created_at FROM otp_challenges
            WHERE email = ? AND purpose = ? AND consumed_at IS NULL
            ORDER BY created_at DESC LIMIT 1
            """,
            (normalized, purpose),
        ).fetchone()
        if recent and (now - recent["created_at"]) < OTP_RESEND_COOLDOWN_SECONDS:
            raise HTTPException(
                status_code=429,
                detail=f"Please wait {OTP_RESEND_COOLDOWN_SECONDS} seconds before requesting a new code.",
            )

        # Invalidate older unconsumed codes
        conn.execute(
            """
            UPDATE otp_challenges SET consumed_at = ?
            WHERE email = ? AND purpose = ? AND consumed_at IS NULL
            """,
            (now, normalized, purpose),
        )

        # Generate cryptographic 6-digit OTP
        otp_code = f"{secrets.randbelow(1_000_000):06d}"
        otp_hash = _hash_otp(normalized, purpose, otp_code)
        challenge_id = f"otp-{secrets.token_hex(10)}"

        conn.execute(
            """
            INSERT INTO otp_challenges (
                id, email, purpose, otp_hash, attempts, max_attempts, expires_at, created_at, ip_address
            ) VALUES (?, ?, ?, ?, 0, ?, ?, ?, ?)
            """,
            (
                challenge_id,
                normalized,
                purpose,
                otp_hash,
                OTP_MAX_ATTEMPTS,
                now + OTP_EXPIRY_SECONDS,
                now,
                ip_address,
            ),
        )

    # Send email outside DB transaction; if SMTP fails, mark challenge invalidated and return 502
    try:
        send_otp_email(normalized, otp_code, expiry_minutes=max(1, OTP_EXPIRY_SECONDS // 60))
    except Exception:
        with get_db() as conn:
            conn.execute(
                "UPDATE otp_challenges SET consumed_at = ? WHERE id = ?",
                (time.time(), challenge_id),
            )
        record_audit_event(
            action="OTP_DELIVERY",
            resource_type="auth",
            outcome="FAILED",
            actor_email=normalized,
            details="SMTP delivery failed",
            ip_address=ip_address,
        )
        raise HTTPException(
            status_code=502,
            detail="Failed to deliver verification email. No session was created.",
        )

    record_audit_event(
        action="OTP_REQUEST",
        resource_type="auth",
        outcome="SUCCESS",
        actor_email=normalized,
        details="Verification code dispatched via SMTP",
        ip_address=ip_address,
    )
    return generic_response


def verify_email_otp(
    email: str, code: str, purpose: str, ip_address: Optional[str], user_agent: Optional[str]
) -> Tuple[str, Dict[str, Any]]:
    normalized = email.strip().lower()
    cleaned_code = code.strip()
    if not EMAIL_RE.match(normalized) or not re.fullmatch(r"\d{6}", cleaned_code):
        raise HTTPException(status_code=400, detail="Invalid email or verification code format")

    if not check_rate_limit(f"otp_verify_ip:{ip_address or 'unknown'}", limit=20, window_seconds=300):
        raise HTTPException(status_code=429, detail="Too many verification attempts.")

    now = time.time()
    audit_to_log: Optional[Dict[str, Any]] = None
    error_detail: Optional[str] = None
    user_id = ""

    with get_db() as conn:
        challenge = conn.execute(
            """
            SELECT * FROM otp_challenges
            WHERE email = ? AND purpose = ? AND consumed_at IS NULL
            ORDER BY created_at DESC LIMIT 1
            """,
            (normalized, purpose),
        ).fetchone()

        if not challenge:
            audit_to_log = {"outcome": "FAILED", "details": "No active OTP challenge"}
            error_detail = "Invalid or expired verification code"
        elif challenge["expires_at"] <= now:
            conn.execute("UPDATE otp_challenges SET consumed_at = ? WHERE id = ?", (now, challenge["id"]))
            audit_to_log = {"outcome": "EXPIRED", "details": "OTP expired"}
            error_detail = "Invalid or expired verification code"
        elif challenge["attempts"] >= challenge["max_attempts"]:
            conn.execute("UPDATE otp_challenges SET consumed_at = ? WHERE id = ?", (now, challenge["id"]))
            audit_to_log = {"outcome": "LOCKED", "details": "Max OTP attempts exceeded"}
            error_detail = "Too many invalid attempts. Request a new code."
        else:
            expected_hash = _hash_otp(normalized, purpose, cleaned_code)
            if not hmac.compare_digest(challenge["otp_hash"], expected_hash):
                conn.execute(
                    "UPDATE otp_challenges SET attempts = attempts + 1 WHERE id = ?",
                    (challenge["id"],),
                )
                audit_to_log = {"outcome": "FAILED", "details": "Incorrect OTP code"}
                error_detail = "Invalid or expired verification code"
            else:
                conn.execute(
                    "UPDATE otp_challenges SET consumed_at = ? WHERE id = ?",
                    (now, challenge["id"]),
                )
                user_row = conn.execute(
                    "SELECT id, status FROM users WHERE lower(email) = ?",
                    (normalized,),
                ).fetchone()
                if user_row and user_row["status"] != "ACTIVE":
                    error_detail = "Account is not active"
                elif user_row:
                    user_id = user_row["id"]
                else:
                    # Auto-provision any verified email ID
                    user_id = f"usr-{secrets.token_hex(8)}"
                    display_name = normalized.split("@")[0]
                    conn.execute(
                        """
                        INSERT INTO users (id, email, full_name, status, platform_role, created_at)
                        VALUES (?, ?, ?, 'ACTIVE', 'USER', ?)
                        """,
                        (user_id, normalized, display_name, now),
                    )
                    first_org = conn.execute(
                        "SELECT id FROM organisations ORDER BY joined_at ASC LIMIT 1"
                    ).fetchone()
                    if first_org:
                        conn.execute(
                            """
                            INSERT INTO memberships (id, user_id, organisation_id, role, created_at)
                            VALUES (?, ?, ?, ?, ?)
                            """,
                            (f"mem-{secrets.token_hex(8)}", user_id, first_org["id"], ROLE_PRIVACY_OFFICER, now),
                        )

    if audit_to_log:
        record_audit_event(
            action="OTP_VERIFY",
            resource_type="auth",
            outcome=audit_to_log["outcome"],
            actor_email=normalized,
            details=audit_to_log["details"],
            ip_address=ip_address,
        )
    if error_detail:
        raise HTTPException(status_code=401, detail=error_detail)

    ctx = load_user_context(user_id)
    if not ctx:
        raise HTTPException(status_code=401, detail="Account is not active")

    raw_token, sess_meta = create_session(
        user_id=user_id,
        active_org_id=ctx["active_org_id"],
        ip_address=ip_address,
        user_agent=user_agent,
    )
    ctx["session_id"] = sess_meta["session_id"]

    record_audit_event(
        action="LOGIN_OTP",
        resource_type="session",
        resource_id=sess_meta["session_id"],
        outcome="SUCCESS",
        actor_id=user_id,
        actor_email=ctx["email"],
        actor_role=ctx["active_role"],
        organisation_id=ctx["active_org_id"],
        details="Authenticated via SMTP Email OTP",
        ip_address=ip_address,
    )
    return raw_token, ctx


# ==============================================================================
# Google OAuth 2.0 / OIDC Logic
# ==============================================================================


def create_google_auth_url(link_user_id: Optional[str] = None) -> Dict[str, str]:
    cfg = get_google_config()
    if not cfg["configured"]:
        raise HTTPException(
            status_code=503,
            detail="Google Sign-In is not configured on this server.",
        )

    state = secrets.token_urlsafe(24)
    nonce = secrets.token_urlsafe(24)
    code_verifier = secrets.token_urlsafe(48)
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    code_challenge = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    now = time.time()

    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO oauth_states (state, nonce, code_verifier, redirect_uri, link_user_id, expires_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (state, nonce, code_verifier, cfg["redirect_uri"], link_user_id, now + 600, now),
        )

    params = {
        "client_id": cfg["client_id"],
        "redirect_uri": cfg["redirect_uri"],
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "nonce": nonce,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "access_type": "online",
        "prompt": "select_account",
    }
    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params)
    return {"auth_url": url, "state": state}


def verify_google_id_token_claims(id_tok: str, client_id: str, expected_nonce: str) -> Dict[str, Any]:
    """Verify Google ID token signature, iss, aud, exp, nonce, and email_verified."""
    req = google_requests.Request()
    claims = google_id_token.verify_oauth2_token(id_tok, req, client_id)

    iss = claims.get("iss")
    if iss not in ("accounts.google.com", "https://accounts.google.com"):
        raise ValueError("Invalid token issuer")
    if claims.get("nonce") != expected_nonce:
        raise ValueError("Invalid OIDC nonce")
    if not claims.get("email_verified"):
        raise ValueError("Google email is not verified")
    if not claims.get("sub") or not claims.get("email"):
        raise ValueError("Missing required identity claims")
    return claims


def handle_google_callback(
    code: str,
    state: str,
    ip_address: Optional[str],
    user_agent: Optional[str],
) -> Tuple[str, Dict[str, Any]]:
    cfg = get_google_config()
    if not cfg["configured"]:
        raise HTTPException(status_code=503, detail="Google Sign-In is not configured.")

    now = time.time()
    with get_db() as conn:
        st = conn.execute("SELECT * FROM oauth_states WHERE state = ?", (state,)).fetchone()
        if not st or st["expires_at"] <= now:
            record_audit_event(
                action="LOGIN_GOOGLE",
                resource_type="auth",
                outcome="FAILED",
                details="Invalid or expired OAuth state",
                ip_address=ip_address,
            )
            raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")

        # Consume state (one-time)
        conn.execute("DELETE FROM oauth_states WHERE state = ?", (state,))
        expected_nonce = st["nonce"]
        code_verifier = st["code_verifier"]
        redirect_uri = st["redirect_uri"]
        link_user_id = st["link_user_id"]

    # Exchange authorization code for tokens
    token_resp = http_requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "code": code,
            "client_id": cfg["client_id"],
            "client_secret": cfg["client_secret"],
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
            "code_verifier": code_verifier,
        },
        timeout=15,
    )
    if token_resp.status_code != 200:
        record_audit_event(
            action="LOGIN_GOOGLE",
            resource_type="auth",
            outcome="FAILED",
            details="Google token exchange failed",
            ip_address=ip_address,
        )
        raise HTTPException(status_code=401, detail="Google authentication failed")

    token_data = token_resp.json()
    raw_id_token = token_data.get("id_token")
    if not raw_id_token:
        raise HTTPException(status_code=401, detail="Missing ID token from Google")

    try:
        claims = verify_google_id_token_claims(raw_id_token, cfg["client_id"], expected_nonce)
    except Exception as exc:
        record_audit_event(
            action="LOGIN_GOOGLE",
            resource_type="auth",
            outcome="FAILED",
            details=f"ID token validation failed: {type(exc).__name__}",
            ip_address=ip_address,
        )
        raise HTTPException(status_code=401, detail="Invalid Google identity token")

    sub = str(claims["sub"])
    email = str(claims["email"]).lower()
    full_name = str(claims.get("name") or email.split("@")[0])

    with get_db() as conn:
        existing_link = conn.execute(
            "SELECT * FROM oauth_identities WHERE provider = 'google' AND provider_sub = ?",
            (sub,),
        ).fetchone()

        if existing_link:
            user_id = existing_link["user_id"]
        elif link_user_id:
            # Explicit authenticated account linking
            oauth_id = f"oauth-{secrets.token_hex(10)}"
            conn.execute(
                """
                INSERT INTO oauth_identities (id, user_id, provider, provider_sub, email, email_verified, created_at)
                VALUES (?, ?, 'google', ?, ?, 1, ?)
                """,
                (oauth_id, link_user_id, sub, email, now),
            )
            user_id = link_user_id
            record_audit_event(
                action="OAUTH_ACCOUNT_LINKED",
                resource_type="user",
                resource_id=user_id,
                outcome="SUCCESS",
                actor_id=user_id,
                actor_email=email,
                details="Linked Google OIDC identity to authenticated account",
                ip_address=ip_address,
            )
        else:
            # Check if an unlinked email-OTP user already exists
            existing_user = conn.execute(
                "SELECT id FROM users WHERE lower(email) = ?", (email,)
            ).fetchone()
            if existing_user:
                # Security requirement: do NOT auto-link solely by email
                record_audit_event(
                    action="OAUTH_LINK_BLOCKED",
                    resource_type="user",
                    resource_id=existing_user["id"],
                    outcome="BLOCKED",
                    actor_email=email,
                    details="Blocked automatic Google link to existing unlinked account",
                    ip_address=ip_address,
                )
                raise HTTPException(
                    status_code=409,
                    detail="An account with this email already exists. Sign in with Email OTP first to link Google.",
                )

            # Create new user + default membership
            user_id = f"usr-{secrets.token_hex(8)}"
            conn.execute(
                """
                INSERT INTO users (id, email, full_name, status, platform_role, created_at)
                VALUES (?, ?, ?, 'ACTIVE', 'USER', ?)
                """,
                (user_id, email, full_name, now),
            )
            # Assign default researcher membership on first active org if present
            first_org = conn.execute("SELECT id FROM organisations ORDER BY joined_at ASC LIMIT 1").fetchone()
            if first_org:
                conn.execute(
                    """
                    INSERT INTO memberships (id, user_id, organisation_id, role, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (f"mem-{secrets.token_hex(8)}", user_id, first_org["id"], ROLE_RESEARCHER, now),
                )
            conn.execute(
                """
                INSERT INTO oauth_identities (id, user_id, provider, provider_sub, email, email_verified, created_at)
                VALUES (?, ?, 'google', ?, ?, 1, ?)
                """,
                (f"oauth-{secrets.token_hex(10)}", user_id, sub, email, now),
            )

    ctx = load_user_context(user_id)
    if not ctx:
        raise HTTPException(status_code=401, detail="Account is not active")

    raw_token, sess_meta = create_session(
        user_id=user_id,
        active_org_id=ctx["active_org_id"],
        ip_address=ip_address,
        user_agent=user_agent,
    )
    ctx["session_id"] = sess_meta["session_id"]

    record_audit_event(
        action="LOGIN_GOOGLE",
        resource_type="session",
        resource_id=sess_meta["session_id"],
        outcome="SUCCESS",
        actor_id=user_id,
        actor_email=ctx["email"],
        actor_role=ctx["active_role"],
        organisation_id=ctx["active_org_id"],
        details="Authenticated via Google OAuth 2.0 / OIDC",
        ip_address=ip_address,
    )
    return raw_token, ctx
