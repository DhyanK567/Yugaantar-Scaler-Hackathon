"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { api } from "@/lib/api";

export default function RegisterPage() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [doneMsg, setDoneMsg] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .authConfig()
      .then((c) => {
        if (c.judge_mode) {
          window.location.replace("/dashboard");
        }
      })
      .catch(() => {});
  }, []);

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
            ONBOARDING
          </div>
          <h1 className="font-serif-display text-[28px] leading-tight text-[#090909]">
            Create account
          </h1>
          <p className="text-[13.5px] text-[#666666] mt-1">
            Register your work email to access MediLocker.
          </p>
        </div>

        {error && (
          <div className="px-3.5 py-2.5 rounded-lg bg-[#FDF2F2] border border-[#E8C5C5] text-[13px] text-[#7F1D1D] mb-4">
            {error}
          </div>
        )}

        {doneMsg ? (
          <div>
            <div className="px-3.5 py-3 rounded-lg bg-[#F4F4F2] border border-[#DADADA] text-[13.5px] text-[#090909] mb-5">
              {doneMsg}
            </div>
            <Link
              href="/login"
              className="block text-center py-2.5 rounded-lg bg-[#090909] text-white text-[13.5px] font-medium hover:bg-[#222222]"
            >
              Continue to Sign In
            </Link>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-[12.5px] font-medium text-[#090909] mb-1.5">
                Full Name
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Dr. Priya Nair"
                required
                className="w-full px-3 py-2.5 rounded-lg bg-[#F4F4F2]/60 border border-[#DADADA] text-[14px] text-[#090909] focus:outline-none focus:border-[#090909]"
              />
            </div>

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
              disabled={loading}
              className="w-full py-2.5 rounded-lg bg-[#090909] text-white text-[13.5px] font-medium hover:bg-[#222222] transition-colors disabled:opacity-50"
            >
              {loading ? "Creating account…" : "Register"}
            </button>
          </form>
        )}

        <div className="text-center mt-6 text-[13px] text-[#666666]">
          Already registered?{" "}
          <Link href="/login" className="text-[#090909] font-medium hover:underline">
            Sign in
          </Link>
        </div>
      </div>
    </div>
  );
}
