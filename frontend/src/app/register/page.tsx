"use client";
import { useState } from "react";
import Link from "next/link";
import Image from "next/image";

export default function RegisterPage() {
  const [form, setForm] = useState({ name: "", email: "", org: "", password: "" });
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    await new Promise((r) => setTimeout(r, 700));
    window.location.href = "/dashboard";
  }

  const Field = ({
    label, name, type = "text", placeholder,
  }: { label: string; name: keyof typeof form; type?: string; placeholder: string }) => (
    <div style={{ marginBottom: 16 }}>
      <label style={{ display: "block", fontSize: 12.5, fontWeight: 500, color: "#050505", marginBottom: 6 }}>
        {label}
      </label>
      <input
        type={type}
        value={form[name]}
        onChange={(e) => setForm((f) => ({ ...f, [name]: e.target.value }))}
        placeholder={placeholder}
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
  );

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
        <p style={{ fontSize: 13.5, color: "#777777", marginBottom: 28 }}>
          Start protecting patient data today.
        </p>

        <form onSubmit={handleSubmit}>
          <Field label="Full Name" name="name" placeholder="Dr. Priya Nair" />
          <Field label="Work Email" name="email" type="email" placeholder="you@hospital.org" />
          <Field label="Organisation" name="org" placeholder="Apollo Hospitals, AIIMS…" />
          <Field label="Password" name="password" type="password" placeholder="••••••••" />

          <button
            type="submit"
            disabled={loading}
            style={{
              width: "100%",
              padding: "12px",
              background: loading ? "#333" : "#050505",
              color: "#FFFFFF",
              border: "none",
              borderRadius: 7,
              fontSize: 14,
              fontWeight: 600,
              cursor: loading ? "not-allowed" : "pointer",
              marginTop: 8,
            }}
          >
            {loading ? "Creating account…" : "Create Free Account"}
          </button>
        </form>

        <div style={{ textAlign: "center", marginTop: 20, fontSize: 13, color: "#777777" }}>
          Already have an account?{" "}
          <Link href="/login" style={{ color: "#050505", fontWeight: 500, textDecoration: "none" }}>
            Sign in
          </Link>
        </div>
      </div>

      <div style={{ marginTop: 24, fontSize: 11.5, color: "#AAAAAA", textAlign: "center" }}>
        Fully offline · No data leaves your environment · CPU-only processing
      </div>
    </div>
  );
}
