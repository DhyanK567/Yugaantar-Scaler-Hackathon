"use client";
import { useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { Mail } from "lucide-react";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    await new Promise((r) => setTimeout(r, 600));
    setSent(true);
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
          <span style={{ fontWeight: 700, fontSize: 18, color: "#050505", letterSpacing: "-0.5px" }}>MediLocker</span>
        </div>
      </Link>

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
        {!sent ? (
          <>
            <div
              style={{
                width: 44,
                height: 44,
                background: "#F2F2F2",
                borderRadius: 10,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                marginBottom: 20,
              }}
            >
              <Mail size={20} color="#050505" />
            </div>
            <h1 style={{ fontSize: 22, fontWeight: 700, color: "#050505", letterSpacing: "-0.5px", marginBottom: 6 }}>
              Reset password
            </h1>
            <p style={{ fontSize: 13.5, color: "#777777", marginBottom: 28 }}>
              Enter your email and we&apos;ll send reset instructions.
            </p>

            <form onSubmit={handleSubmit}>
              <label style={{ display: "block", fontSize: 12.5, fontWeight: 500, color: "#050505", marginBottom: 6 }}>
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
                  marginBottom: 20,
                }}
              />
              <button
                type="submit"
                style={{
                  width: "100%",
                  padding: "12px",
                  background: "#050505",
                  color: "#FFFFFF",
                  border: "none",
                  borderRadius: 7,
                  fontSize: 14,
                  fontWeight: 600,
                  cursor: "pointer",
                }}
              >
                Send Reset Link
              </button>
            </form>
          </>
        ) : (
          <div style={{ textAlign: "center" }}>
            <div
              style={{
                width: 56,
                height: 56,
                background: "#050505",
                borderRadius: "50%",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                margin: "0 auto 20px",
              }}
            >
              <Mail size={24} color="#FFFFFF" />
            </div>
            <h2 style={{ fontSize: 20, fontWeight: 700, color: "#050505", marginBottom: 10 }}>
              Check your inbox
            </h2>
            <p style={{ fontSize: 13.5, color: "#666666", marginBottom: 24 }}>
              Reset instructions sent to <strong>{email}</strong>
            </p>
            <Link href="/login" style={{ fontSize: 14, color: "#050505", fontWeight: 500, textDecoration: "none" }}>
              Back to Sign In →
            </Link>
          </div>
        )}

        {!sent && (
          <div style={{ textAlign: "center", marginTop: 20, fontSize: 13, color: "#777777" }}>
            <Link href="/login" style={{ color: "#050505", fontWeight: 500, textDecoration: "none" }}>
              ← Back to Sign In
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}
