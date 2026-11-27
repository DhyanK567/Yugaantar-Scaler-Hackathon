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
    api
      .authConfig()
      .then((c) => {
        if (c.judge_mode) {
          window.location.replace("/dashboard");
          return;
        }
        setConfig(c);
      })
      .catch(() => {});
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
    <div className="min-h-screen bg-[#F4F4F2] flex flex-col items-center justify-center p-6">
      <Link href="/" className="flex items-center gap-2.5 mb-8">
        <Image
          src="/medilocker-logo.jpg"
          alt="MediLocker"
          width={34}
          height={34}
          className="rounded-full"
        />
        <span className="font-serif-display text-[22px] text-[#090909]">
          MediLocker
        </span>
      </Link>

      <div className="bg-white border border-[#DADADA] rounded-2xl p-8 sm:p-9 w-full max-w-[420px]">
        <div className="mb-6">
          <div className="text-[10.5px] font-semibold uppercase tracking-[0.1em] text-[#888888] mb-1.5">
            ACCESS CONSOLE
          </div>
          <h1 className="font-serif-display text-[28px] leading-tight text-[#090909]">
            Sign in to MediLocker
          </h1>
          <p className="text-[13.5px] text-[#666666] mt-1">
            Passwordless healthcare privacy authentication.
          </p>
        </div>

        {error && (
          <div className="px-3.5 py-2.5 rounded-lg bg-[#FDF2F2] border border-[#E8C5C5] text-[13px] text-[#7F1D1D] mb-4">
            {error}
          </div>
        )}

        {info && (
          <div className="px-3.5 py-2.5 rounded-lg bg-[#F4F4F2] border border-[#DADADA] text-[13px] text-[#090909] mb-4">
            {info}
          </div>
        )}

        {config?.offline_mode && (
          <div className="p-4 rounded-xl bg-[#F4F4F2] border border-[#090909] mb-5">
            <div className="text-[11.5px] font-semibold uppercase tracking-[0.06em] text-[#090909] mb-1">
              Offline Local Demo Mode
            </div>
            <p className="text-[12px] text-[#666666] mb-3 leading-relaxed">
              Running locally on loopback (127.0.0.1). No internet, SMTP, or Google OAuth required.
            </p>
            <button
              type="button"
              onClick={handleOfflineDemo}
              disabled={loading}
              className="w-full py-2.5 rounded-lg bg-[#090909] text-white text-[13px] font-medium hover:bg-[#222222] transition-colors disabled:opacity-50"
            >
              Continue in Offline Demo Mode
            </button>
          </div>
        )}

        {step === "email" ? (
          <form onSubmit={handleRequestOtp} className="space-y-4">
            <div>
              <label className="block text-[12.5px] font-medium text-[#090909] mb-1.5">
                Work Email
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@hospital.org"
                required
                className="w-full px-3 py-2.5 rounded-lg bg-[#F4F4F2]/60 border border-[#DADADA] text-[14px] text-[#090909] focus:outline-none focus:border-[#090909]"
              />
            </div>

            <button
              type="submit"
              disabled={
                loading ||
                (config !== null && !config.smtp_enabled && !config.dev_email_login_enabled)
              }
              className="w-full py-2.5 rounded-lg bg-[#090909] text-white text-[13.5px] font-medium hover:bg-[#222222] transition-colors disabled:bg-[#888888] disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              <Mail size={15} />
              <span>
                {loading
                  ? "Signing in…"
                  : config && !config.smtp_enabled && config.dev_email_login_enabled
                  ? "Continue with Email"
                  : "Send verification code"}
              </span>
            </button>

            {config && !config.smtp_enabled && !config.dev_email_login_enabled && (
              <p className="text-[11.5px] text-[#888888]">
                Email OTP unavailable: SMTP_HOST is not configured on backend.
              </p>
            )}
          </form>
        ) : (
          <form onSubmit={handleVerifyOtp} className="space-y-4">
            <button
              type="button"
              onClick={() => {
                setStep("email");
                setCode("");
                setError("");
              }}
              className="inline-flex items-center gap-1.5 text-[12.5px] text-[#666666] hover:text-[#090909]"
            >
              <ArrowLeft size={13} />
              <span>Change email ({email})</span>
            </button>

            <div>
              <label className="block text-[12.5px] font-medium text-[#090909] mb-1.5">
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
                className="w-full px-3 py-2.5 rounded-lg bg-[#F4F4F2]/60 border border-[#DADADA] text-[18px] tracking-[0.25em] text-center text-[#090909] focus:outline-none focus:border-[#090909]"
              />
            </div>

            <button
              type="submit"
              disabled={loading || code.length !== 6}
              className="w-full py-2.5 rounded-lg bg-[#090909] text-white text-[13.5px] font-medium hover:bg-[#222222] transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
            >
              <ShieldCheck size={15} />
              <span>{loading ? "Verifying…" : "Verify & Continue"}</span>
            </button>
          </form>
        )}

        <div className="flex items-center gap-3 my-5">
          <div className="flex-1 h-px bg-[#E5E5E5]" />
          <span className="text-[11px] uppercase tracking-wider text-[#888888]">or</span>
          <div className="flex-1 h-px bg-[#E5E5E5]" />
        </div>

        <button
          type="button"
          onClick={handleGoogleLogin}
          disabled={config !== null && !config.google_enabled}
          className="w-full py-2.5 px-4 rounded-lg bg-white border border-[#DADADA] text-[13.5px] font-medium text-[#090909] hover:bg-[#F4F4F2] transition-colors disabled:text-[#888888] disabled:cursor-not-allowed flex items-center justify-center gap-2.5"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" aria-hidden="true">
            <path fill="#4285F4" d="M23.745 12.27c0-.7-.06-1.4-.19-2.07H12v4.51h6.6c-.29 1.52-1.14 2.82-2.4 3.68v3.05h3.88c2.27-2.09 3.665-5.17 3.665-9.17z" />
            <path fill="#34A853" d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.88-3.05c-1.08.72-2.45 1.16-4.05 1.16-3.12 0-5.77-2.11-6.72-4.96H1.29v3.14C3.26 21.3 7.31 24 12 24z" />
            <path fill="#FBBC05" d="M5.28 14.24c-.24-.72-.38-1.49-.38-2.24s.14-1.52.38-2.24V6.62H1.29C.47 8.24 0 10.06 0 12s.47 3.76 1.29 5.38l3.99-3.14z" />
            <path fill="#EA4335" d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.95 1.19 15.24 0 12 0 7.31 0 3.26 2.7 1.29 6.62l3.99 3.14c.95-2.85 3.6-4.96 6.72-4.96z" />
          </svg>
          <span>Continue with Google</span>
        </button>

        <div className="text-center mt-6 text-[13px] text-[#666666]">
          Need an account?{" "}
          <Link href="/register" className="text-[#090909] font-medium hover:underline">
            Register
          </Link>
        </div>
      </div>

      <div className="mt-6 text-[11.5px] text-[#888888] text-center">
        Offline privacy engine remains independent of web login
      </div>
    </div>
  );
}
