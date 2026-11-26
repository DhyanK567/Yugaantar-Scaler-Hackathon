"use client";
import { useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { Eye, EyeOff, Lock } from "lucide-react";

export default function LoginPage() {
  const [show, setShow] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    // Minimal frontend session gate — backend has no auth endpoint
    // In production this would call POST /api/auth/login
    await new Promise((r) => setTimeout(r, 600));
    if (email && password.length >= 6) {
      window.location.href = "/dashboard";
    } else {
      setError("Please enter a valid email and password (min 6 chars).");
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
      {/* Logo */}
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

      {/* Card */}
      <div
        style={{
          background: "#FFFFFF",
          border: "1.5px solid #DCDCDC",
          borderRadius: 12,
          padding: "40px 36px",
          width: "100%",
          maxWidth: 400,
        }}
      >
        <div style={{ marginBottom: 28 }}>
          <h1
            style={{
              fontSize: 22,
              fontWeight: 700,
              color: "#050505",
              letterSpacing: "-0.5px",
              marginBottom: 6,
            }}
          >
            Sign in
          </h1>
          <p style={{ fontSize: 13.5, color: "#777777" }}>
            Access your privacy infrastructure console.
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

        <form onSubmit={handleSubmit}>
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
              Email
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
                boxSizing: "border-box",
              }}
            />
          </div>

          <div style={{ marginBottom: 24 }}>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: 6,
              }}
            >
              <label
                style={{ fontSize: 12.5, fontWeight: 500, color: "#050505" }}
              >
                Password
              </label>
              <Link
                href="/forgot-password"
                style={{ fontSize: 12, color: "#777777", textDecoration: "none" }}
              >
                Forgot password?
              </Link>
            </div>
            <div style={{ position: "relative" }}>
              <input
                type={show ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                required
                style={{
                  width: "100%",
                  padding: "10px 40px 10px 12px",
                  border: "1.5px solid #DCDCDC",
                  borderRadius: 7,
                  fontSize: 14,
                  color: "#050505",
                  background: "#FAFAFA",
                  outline: "none",
                  boxSizing: "border-box",
                }}
              />
              <button
                type="button"
                onClick={() => setShow(!show)}
                style={{
                  position: "absolute",
                  right: 10,
                  top: "50%",
                  transform: "translateY(-50%)",
                  background: "none",
                  border: "none",
                  cursor: "pointer",
                  color: "#777777",
                  padding: 0,
                  display: "flex",
                }}
              >
                {show ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
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
            {loading ? (
              "Signing in…"
            ) : (
              <>
                <Lock size={14} />
                Sign In Securely
              </>
            )}
          </button>
        </form>

        <div
          style={{
            textAlign: "center",
            marginTop: 20,
            fontSize: 13,
            color: "#777777",
          }}
        >
          Don&apos;t have an account?{" "}
          <Link
            href="/register"
            style={{ color: "#050505", fontWeight: 500, textDecoration: "none" }}
          >
            Create one
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
        Fully offline · No data leaves your environment · CPU-only processing
      </div>
    </div>
  );
}
