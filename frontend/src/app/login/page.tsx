"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { Mail, ArrowLeft, ShieldCheck } from "lucide-react";
import { api, type AuthConfig } from "@/lib/api";

export default function LoginPage() {
  const [config, setConfig] = useState<AuthConfig | null>(null);
  const [step, setStep] = useState<"email" | "otp">("email");
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [info, setInfo] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    api.authConfig().then(setConfig).catch(() => {});
  }, []);

  async function handleRequestOtp(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    setInfo("");
    try {
      if (config && !config.smtp_enabled && config.dev_email_login_enabled) {
        await api.devEmailLogin(email);
        window.location.href = "/dashboard";
        return;
      }
      const res = await api.requestOtp(email);
      setInfo(res.message);
      setStep("otp");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to send verification code.");
    }
    setLoading(false);
  }

  async function handleVerifyOtp(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      await api.verifyOtp(email, code);
      window.location.href = "/dashboard";
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Invalid verification code.");
    }
    setLoading(false);
  }

  async function handleGoogleLogin() {
    setError("");
    try {
      const res = await api.googleLoginUrl();
      window.location.href = res.auth_url;
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Google Sign-In unavailable.");
    }
  }

  async function handleOfflineDemo() {
    setLoading(true);
    setError("");
    try {
      await api.offlineDemoLogin(email || undefined);
      window.location.href = "/dashboard";
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Offline demo login failed.");
    }
    setLoading(false);
  }

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "#F2F2F2",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: 24,
      }}
    >
      <Link href="/" style={{ textDecoration: "none", marginBottom: 32 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <Image
            src="/medilocker-logo.jpg"
            alt="MediLocker"
            width={36}
            height={36}
            style={{ borderRadius: "50%" }}
          />
          <span
            style={{
              fontWeight: 700,
              fontSize: 18,
              color: "#050505",
              letterSpacing: "-0.5px",
            }}
          >
            MediLocker
          </span>
        </div>
      </Link>

      <div
        style={{
          background: "#FFFFFF",
          border: "1.5px solid #DCDCDC",
          borderRadius: 12,
          padding: "36px 34px",
          width: "100%",
          maxWidth: 420,
        }}
      >
        <div style={{ marginBottom: 24 }}>
          <h1
            style={{
              fontSize: 22,
              fontWeight: 700,
              color: "#050505",
              letterSpacing: "-0.5px",
              marginBottom: 6,
            }}
          >
            Sign in to MediLocker
          </h1>
          <p style={{ fontSize: 13.5, color: "#777777" }}>
            Passwordless healthcare privacy authentication.
          </p>
        </div>

        {error && (
          <div
            style={{
              padding: "10px 14px",
              background: "#FFF5F5",
              border: "1px solid #FFD5D5",
              borderRadius: 6,
              fontSize: 13,
              color: "#CC3333",
              marginBottom: 16,
            }}
          >
            {error}
          </div>
        )}

        {info && (
          <div
            style={{
              padding: "10px 14px",
              background: "#F5F5F5",
              border: "1px solid #DCDCDC",
              borderRadius: 6,
              fontSize: 13,
              color: "#050505",
              marginBottom: 16,
            }}
          >
            {info}
          </div>
        )}

        {config?.offline_mode && (
          <div
            style={{
              padding: "12px 14px",
              background: "#F2F2F2",
              border: "1.5px solid #050505",
              borderRadius: 8,
              marginBottom: 18,
            }}
          >
            <div style={{ fontSize: 12, fontWeight: 700, color: "#050505", marginBottom: 4 }}>
              Offline Local Demo Mode Active
            </div>
            <div style={{ fontSize: 12, color: "#555555", marginBottom: 10 }}>
              Running 100% locally on loopback (127.0.0.1). No internet, SMTP, or Google OAuth required.
            </div>
            <button
              type="button"
              onClick={handleOfflineDemo}
              disabled={loading}
              style={{
                width: "100%",
                padding: "10px 14px",
                background: "#050505",
                color: "#FFFFFF",
                border: "none",
                borderRadius: 6,
                fontSize: 13.5,
                fontWeight: 600,
                cursor: loading ? "not-allowed" : "pointer",
              }}
            >
              Continue in Offline Demo Mode
            </button>
          </div>
        )}

        {step === "email" ? (
          <form onSubmit={handleRequestOtp}>
            <div style={{ marginBottom: 16 }}>
              <label
                style={{
                  display: "block",
                  fontSize: 12.5,
                  fontWeight: 500,
                  color: "#050505",
                  marginBottom: 6,
                }}
              >
                Work Email
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@hospital.org"
                required
                style={{
                  width: "100%",
                  padding: "10px 12px",
                  border: "1.5px solid #DCDCDC",
                  borderRadius: 7,
                  fontSize: 14,
                  color: "#050505",
                  background: "#FAFAFA",
                  outline: "none",
                }}
              />
            </div>

            <button
              type="submit"
              disabled={
                loading ||
                (config !== null && !config.smtp_enabled && !config.dev_email_login_enabled)
              }
              style={{
                width: "100%",
                padding: "12px",
                background:
                  loading ||
                  (config !== null && !config.smtp_enabled && !config.dev_email_login_enabled)
                    ? "#777777"
                    : "#050505",
                color: "#FFFFFF",
                border: "none",
                borderRadius: 7,
                fontSize: 14,
                fontWeight: 600,
                cursor:
                  loading ||
                  (config !== null && !config.smtp_enabled && !config.dev_email_login_enabled)
                    ? "not-allowed"
                    : "pointer",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: 8,
              }}
            >
              <Mail size={15} />
              {loading
                ? "Signing in…"
                : config && !config.smtp_enabled && config.dev_email_login_enabled
                ? "Continue with Email"
                : "Send verification code"}
            </button>

            {config && !config.smtp_enabled && config.dev_email_login_enabled && (
              <div style={{ fontSize: 11.5, color: "#666666", marginTop: 8 }}>
                Local dev mode: SMTP is not configured, so any valid email signs in directly.
              </div>
            )}
            {config && !config.smtp_enabled && !config.dev_email_login_enabled && (
              <div style={{ fontSize: 11.5, color: "#777777", marginTop: 8 }}>
                Email OTP unavailable: SMTP_HOST is not configured on backend.
              </div>
            )}
          </form>
        ) : (
          <form onSubmit={handleVerifyOtp}>
            <button
              type="button"
              onClick={() => {
                setStep("email");
                setCode("");
                setError("");
              }}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 5,
                background: "none",
                border: "none",
                padding: 0,
                fontSize: 12.5,
                color: "#777777",
                cursor: "pointer",
                marginBottom: 14,
              }}
            >
              <ArrowLeft size={13} />
              Change email ({email})
            </button>

            <div style={{ marginBottom: 16 }}>
              <label
                style={{
                  display: "block",
                  fontSize: 12.5,
                  fontWeight: 500,
                  color: "#050505",
                  marginBottom: 6,
                }}
              >
                6-Digit Verification Code
              </label>
              <input
                type="text"
                inputMode="numeric"
                maxLength={6}
                value={code}
                onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
                placeholder="123456"
                required
                style={{
                  width: "100%",
                  padding: "10px 12px",
                  border: "1.5px solid #DCDCDC",
                  borderRadius: 7,
                  fontSize: 18,
                  letterSpacing: "4px",
                  textAlign: "center",
                  color: "#050505",
                  background: "#FAFAFA",
                  outline: "none",
                }}
              />
            </div>

            <button
              type="submit"
              disabled={loading || code.length !== 6}
              style={{
                width: "100%",
                padding: "12px",
                background: loading ? "#333333" : "#050505",
                color: "#FFFFFF",
                border: "none",
                borderRadius: 7,
                fontSize: 14,
                fontWeight: 600,
                cursor: loading ? "not-allowed" : "pointer",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: 8,
              }}
            >
              <ShieldCheck size={15} />
              {loading ? "Verifying…" : "Verify & Continue"}
            </button>
          </form>
        )}

        {/* Divider */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 12,
            margin: "22px 0",
          }}
        >
          <div style={{ flex: 1, height: 1, background: "#E6E6E6" }} />
          <span style={{ fontSize: 11.5, color: "#777777", textTransform: "uppercase" }}>or</span>
          <div style={{ flex: 1, height: 1, background: "#E6E6E6" }} />
        </div>

        {/* Official Google Sign-In Button */}
        <button
          type="button"
          onClick={handleGoogleLogin}
          disabled={config !== null && !config.google_enabled}
          style={{
            width: "100%",
            padding: "11px 16px",
            background: "#FFFFFF",
            color: config !== null && !config.google_enabled ? "#999999" : "#1F1F1F",
            border: "1.5px solid #DCDCDC",
            borderRadius: 7,
            fontSize: 14,
            fontWeight: 500,
            cursor: config !== null && !config.google_enabled ? "not-allowed" : "pointer",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: 10,
          }}
        >
          <svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true">
            <path
              fill="#4285F4"
              d="M23.745 12.27c0-.7-.06-1.4-.19-2.07H12v4.51h6.6c-.29 1.52-1.14 2.82-2.4 3.68v3.05h3.88c2.27-2.09 3.665-5.17 3.665-9.17z"
            />
            <path
              fill="#34A853"
              d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.88-3.05c-1.08.72-2.45 1.16-4.05 1.16-3.12 0-5.77-2.11-6.72-4.96H1.29v3.14C3.26 21.3 7.31 24 12 24z"
            />
            <path
              fill="#FBBC05"
              d="M5.28 14.24c-.24-.72-.38-1.49-.38-2.24s.14-1.52.38-2.24V6.62H1.29C.47 8.24 0 10.06 0 12s.47 3.76 1.29 5.38l3.99-3.14z"
            />
            <path
              fill="#EA4335"
              d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.95 1.19 15.24 0 12 0 7.31 0 3.26 2.7 1.29 6.62l3.99 3.14c.95-2.85 3.6-4.96 6.72-4.96z"
            />
          </svg>
          Continue with Google
        </button>
        {config && !config.google_enabled && (
          <div style={{ fontSize: 11.5, color: "#777777", marginTop: 8, textAlign: "center" }}>
            Google Sign-In is disabled (GOOGLE_CLIENT_ID not configured).
          </div>
        )}

        <div
          style={{
            textAlign: "center",
            marginTop: 22,
            fontSize: 13,
            color: "#777777",
          }}
        >
          Need an account?{" "}
          <Link
            href="/register"
            style={{ color: "#050505", fontWeight: 500, textDecoration: "none" }}
          >
            Register
          </Link>
        </div>
      </div>

      <div
        style={{
          marginTop: 24,
          fontSize: 11.5,
          color: "#AAAAAA",
          textAlign: "center",
        }}
      >
        Offline privacy engine remains independent of web login
      </div>
    </div>
  );
}
