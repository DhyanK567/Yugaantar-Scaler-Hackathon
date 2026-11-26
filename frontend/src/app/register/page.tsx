"use client";
import { useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { api } from "@/lib/api";

export default function RegisterPage() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [doneMsg, setDoneMsg] = useState("");
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const res = await api.register(email, name);
      setDoneMsg(res.message);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Registration failed.");
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
          <Image src="/medilocker-logo.jpg" alt="MediLocker" width={36} height={36} style={{ borderRadius: "50%" }} />
          <span style={{ fontWeight: 700, fontSize: 18, color: "#050505", letterSpacing: "-0.5px" }}>
            MediLocker
          </span>
        </div>
      </Link>

      <div
        style={{
          background: "#FFFFFF",
          border: "1.5px solid #DCDCDC",
          borderRadius: 12,
          padding: "40px 36px",
          width: "100%",
          maxWidth: 420,
        }}
      >
        <h1 style={{ fontSize: 22, fontWeight: 700, color: "#050505", letterSpacing: "-0.5px", marginBottom: 6 }}>
          Create account
        </h1>
        <p style={{ fontSize: 13.5, color: "#777777", marginBottom: 24 }}>
          Register your work email to sign in with Email OTP.
        </p>

        {error && (
          <div style={{ padding: "10px 14px", background: "#FFF5F5", border: "1px solid #FFD5D5", borderRadius: 6, fontSize: 13, color: "#CC3333", marginBottom: 16 }}>
            {error}
          </div>
        )}

        {doneMsg ? (
          <div>
            <div style={{ padding: "12px 14px", background: "#F5F5F5", border: "1px solid #DCDCDC", borderRadius: 6, fontSize: 13.5, color: "#050505", marginBottom: 20 }}>
              {doneMsg}
            </div>
            <Link
              href="/login"
              style={{
                display: "block",
                textAlign: "center",
                padding: "12px",
                background: "#050505",
                color: "#FFFFFF",
                borderRadius: 7,
                textDecoration: "none",
                fontSize: 14,
                fontWeight: 600,
              }}
            >
              Continue to Sign In
            </Link>
          </div>
        ) : (
          <form onSubmit={handleSubmit}>
            <div style={{ marginBottom: 16 }}>
              <label style={{ display: "block", fontSize: 12.5, fontWeight: 500, color: "#050505", marginBottom: 6 }}>
                Full Name
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Dr. Priya Nair"
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

            <div style={{ marginBottom: 20 }}>
              <label style={{ display: "block", fontSize: 12.5, fontWeight: 500, color: "#050505", marginBottom: 6 }}>
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
              }}
            >
              {loading ? "Creating account…" : "Register"}
            </button>
          </form>
        )}

        <div style={{ textAlign: "center", marginTop: 20, fontSize: 13, color: "#777777" }}>
          Already registered?{" "}
          <Link href="/login" style={{ color: "#050505", fontWeight: 500, textDecoration: "none" }}>
            Sign in
          </Link>
        </div>
      </div>
    </div>
  );
}
