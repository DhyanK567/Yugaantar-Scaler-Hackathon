"use client";

import { useState } from "react";
import Link from "next/link";
import MarketingNav from "@/components/layout/MarketingNav";
import { Check } from "lucide-react";

const PLANS = [
  {
    id: "starter",
    name: "STARTER",
    price: { monthly: "Free", annually: "Free" },
    description: "For individual researchers and offline evaluation.",
    cta: "Get started",
    ctaHref: "/register",
    dark: false,
    features: [
      "Offline CPU-only CLI & local console",
      "CSV, TSV, JSON, plain text",
      "Multilingual PII detection (English/Hindi/Hinglish)",
      "HMAC-SHA256 pseudonymisation",
      "Unsigned SHA-256 Privacy Passport",
    ],
  },
  {
    id: "pro",
    name: "INSTITUTION",
    price: { monthly: "₹4,999", annually: "₹3,999" },
    suffix: "/mo",
    description: "For hospitals, diagnostic labs and clinical registries.",
    cta: "Get started",
    ctaHref: "/register",
    dark: true,
    badge: "RECOMMENDED",
    features: [
      "Everything in Starter",
      "HL7 FHIR R4 Bundle validation",
      "Cross-hospital identity continuity",
      "7-vector re-identification attack simulator",
      "Role-based access control & audit trail",
      "Research collaboration governance",
    ],
  },
  {
    id: "enterprise",
    name: "CONSORTIUM",
    price: { monthly: "Custom", annually: "Custom" },
    description: "For multi-hospital networks and public health agencies.",
    cta: "Open console",
    ctaHref: "/dashboard",
    dark: false,
    features: [
      "Everything in Institution",
      "Air-gapped on-premise deployment",
      "Custom policy.yaml thresholds",
      "Multi-organisation isolation",
      "Dedicated compliance documentation",
    ],
  },
];

export default function PricingPage() {
  const [annual, setAnnual] = useState(true);

  return (
    <div className="min-h-screen bg-[#F4F4F2] text-[#090909]">
      <MarketingNav />

      <div className="max-w-[1100px] mx-auto px-6 py-16 sm:py-24">
        <div className="text-center max-w-2xl mx-auto mb-14">
          <div className="text-[11px] font-semibold uppercase tracking-[0.12em] text-[#666666] mb-3">
            DEPLOYMENT TIERS
          </div>
          <h1 className="font-serif-display text-[40px] sm:text-[56px] leading-[1.06] tracking-[-0.02em] text-[#090909] mb-4">
            Simple, transparent infrastructure.
          </h1>
          <p className="text-[15px] text-[#666666] leading-relaxed mb-8">
            Run offline for free on local hardware, or deploy across hospital networks.
          </p>

          <div className="inline-flex bg-white border border-[#DADADA] rounded-full p-1">
            {[
              { label: "Monthly", val: false },
              { label: "Annually", val: true },
            ].map((opt) => (
              <button
                key={opt.label}
                type="button"
                onClick={() => setAnnual(opt.val)}
                className={`px-5 py-1.5 rounded-full text-[13px] font-medium transition-colors ${
                  annual === opt.val
                    ? "bg-[#090909] text-white"
                    : "text-[#666666] hover:text-[#090909]"
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 items-stretch">
          {PLANS.map((plan) => (
            <div
              key={plan.id}
              className={`relative rounded-2xl border p-7 flex flex-col ${
                plan.dark
                  ? "bg-[#090909] text-white border-[#090909]"
                  : "bg-white text-[#090909] border-[#DADADA]"
              }`}
            >
              {plan.badge && (
                <div className="absolute -top-3 left-6 bg-white text-[#090909] border border-[#DADADA] rounded-full px-3 py-0.5 text-[10px] font-semibold tracking-[0.06em]">
                  {plan.badge}
                </div>
              )}

              <div className="text-[11px] font-semibold uppercase tracking-[0.1em] text-[#888888] mb-3">
                {plan.name}
              </div>

              <div className="font-serif-display text-[42px] leading-none mb-3">
                {annual ? plan.price.annually : plan.price.monthly}
                {plan.suffix && (
                  <span className="font-sans-ui text-[14px] text-[#888888] ml-1">
                    {plan.suffix}
                  </span>
                )}
              </div>

              <p className={`text-[13px] mb-6 ${plan.dark ? "text-[#B5B5B5]" : "text-[#666666]"}`}>
                {plan.description}
              </p>

              <Link
                href={plan.ctaHref}
                className={`block text-center py-2.5 rounded-full text-[13.5px] font-medium transition-colors mb-6 ${
                  plan.dark
                    ? "bg-white text-[#090909] hover:bg-[#E6E6E6]"
                    : "bg-[#090909] text-white hover:bg-[#222222]"
                }`}
              >
                {plan.cta}
              </Link>

              <div className="space-y-2.5 pt-5 border-t border-[#E5E5E5]/20 flex-1">
                {plan.features.map((f) => (
                  <div key={f} className="flex items-start gap-2.5 text-[13px]">
                    <Check
                      size={14}
                      className={`shrink-0 mt-0.5 ${plan.dark ? "text-white" : "text-[#090909]"}`}
                    />
                    <span className={plan.dark ? "text-[#E6E6E6]" : "text-[#444444]"}>{f}</span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
