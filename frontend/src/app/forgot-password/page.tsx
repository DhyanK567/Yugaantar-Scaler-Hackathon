"use client";

import Link from "next/link";
import Image from "next/image";
import { Mail } from "lucide-react";

export default function ForgotPasswordPage() {
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

      <div className="bg-white border border-[#DADADA] rounded-2xl p-8 sm:p-9 w-full max-w-[420px] text-center">
        <div className="w-11 h-11 rounded-full bg-[#F4F4F2] border border-[#E5E5E5] flex items-center justify-center mx-auto mb-4">
          <Mail size={18} className="text-[#090909]" />
        </div>
        <h1 className="font-serif-display text-[26px] text-[#090909] mb-2">
          Passwordless Authentication
        </h1>
        <p className="text-[13.5px] text-[#666666] leading-relaxed mb-6">
          MediLocker uses one-time Email OTP, Google OAuth, or Offline Local Demo Mode instead of static passwords.
        </p>
        <Link
          href="/login"
          className="inline-block w-full py-2.5 rounded-lg bg-[#090909] text-white text-[13.5px] font-medium hover:bg-[#222222]"
        >
          Return to Sign In
        </Link>
      </div>
    </div>
  );
}
