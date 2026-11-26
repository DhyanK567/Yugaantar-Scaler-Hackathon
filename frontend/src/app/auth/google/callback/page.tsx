"use client";
import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";

function GoogleCallbackInner() {
  const params = useSearchParams();
  const [error, setError] = useState("");

  useEffect(() => {
    const code = params.get("code");
    const state = params.get("state");
    if (!code || !state) {
      setError("Missing OAuth code or state parameter.");
      return;
    }
    api
      .googleCallback(code, state)
      .then(() => {
        window.location.href = "/dashboard";
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : "Google authentication failed.");
      });
  }, [params]);

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "#F2F2F2",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: 24,
      }}
    >
      <div
        style={{
          background: "#FFFFFF",
          border: "1.5px solid #DCDCDC",
          borderRadius: 12,
          padding: "36px 32px",
          maxWidth: 420,
          width: "100%",
          textAlign: "center",
        }}
      >
        {error ? (
          <>
            <h1 style={{ fontSize: 18, fontWeight: 700, color: "#CC3333", marginBottom: 8 }}>
              Sign-In Error
            </h1>
            <p style={{ fontSize: 13.5, color: "#555555", marginBottom: 20 }}>{error}</p>
            <Link
              href="/login"
              style={{
                display: "inline-block",
                padding: "10px 20px",
                background: "#050505",
                color: "#FFFFFF",
                borderRadius: 7,
                textDecoration: "none",
                fontSize: 13.5,
                fontWeight: 600,
              }}
            >
              Return to Sign In
            </Link>
          </>
        ) : (
          <p style={{ fontSize: 14, color: "#050505" }}>Completing Google Sign-In…</p>
        )}
      </div>
    </div>
  );
}

export default function GoogleCallbackPage() {
  return (
    <Suspense fallback={<div style={{ padding: 40, textAlign: "center" }}>Loading…</div>}>
      <GoogleCallbackInner />
    </Suspense>
  );
}
