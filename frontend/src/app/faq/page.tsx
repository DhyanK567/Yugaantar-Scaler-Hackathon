"use client";

import { useState } from "react";
import MarketingNav from "@/components/layout/MarketingNav";
import { ChevronDown } from "lucide-react";

const FAQS = [
  {
    category: "ARCHITECTURE & OFFLINE EXECUTION",
    questions: [
      {
        q: "Does MediLocker require internet access, LLMs, or external AI APIs?",
        a: "No. The core privacy engine (starter/main.py) runs 100% offline on CPU using Python standard library deterministic algorithms, regexes, phonetic matching, and HMAC-SHA256 pseudonymisation.",
      },
      {
        q: "What file formats are supported?",
        a: "MediLocker processes CSV, TSV, JSON, JSONL, HL7 FHIR R4 Bundles, and plain-text clinical notes. Unsupported or malformed binaries (such as PDF or PNG) are safely quarantined.",
      },
    ],
  },
  {
    category: "PRIVACY, IDENTITY & CLINICAL INTEGRITY",
    questions: [
      {
        q: "How does cross-hospital identity continuity avoid false merges?",
        a: "Records are clustered conservatively using strong identifiers (Phone, Aadhaar, ABHA, PAN, MRN/UHID) and corroborated transliterated names with demographic compatibility checks. Uncertain pairs abstain rather than merging.",
      },
      {
        q: "Are clinical measurements and FHIR R4 structures preserved?",
        a: "Yes. Medical eponyms, dosages, laboratory units, and FHIR R4 structural references are protected by clinical guards and verified post-sanitisation.",
      },
      {
        q: "What is an UNSIGNED Privacy Passport?",
        a: "Every completed job emits a Privacy Passport manifest containing a SHA-256 integrity hash over its measured metrics and release decision. Because no PKI signing key is provisioned by default, manifests are explicitly labelled UNSIGNED.",
      },
    ],
  },
];

export default function FAQPage() {
  const [openKey, setOpenKey] = useState<string | null>("0-0");

  return (
    <div className="min-h-screen bg-[#F4F4F2] text-[#090909]">
      <MarketingNav />

      <div className="max-w-[900px] mx-auto px-6 py-16 sm:py-24">
        <div className="mb-14">
          <div className="text-[11px] font-semibold uppercase tracking-[0.12em] text-[#666666] mb-3">
            FREQUENTLY ASKED QUESTIONS
          </div>
          <h1 className="font-serif-display text-[40px] sm:text-[54px] leading-[1.08] tracking-[-0.02em] text-[#090909]">
            Clear answers for privacy teams and auditors.
          </h1>
        </div>

        <div className="space-y-12">
          {FAQS.map((sec, sIdx) => (
            <div key={sec.category}>
              <div className="text-[11px] font-semibold uppercase tracking-[0.1em] text-[#888888] pb-3 border-b border-[#DADADA]">
                {sec.category}
              </div>
              <div>
                {sec.questions.map((item, qIdx) => {
                  const key = `${sIdx}-${qIdx}`;
                  const isOpen = openKey === key;
                  return (
                    <div key={item.q} className="border-b border-[#E5E5E5]">
                      <button
                        type="button"
                        onClick={() => setOpenKey(isOpen ? null : key)}
                        className="w-full py-5 flex items-center justify-between gap-4 text-left"
                      >
                        <span className="text-[15.5px] font-medium text-[#090909]">
                          {item.q}
                        </span>
                        <ChevronDown
                          size={18}
                          className={`text-[#666666] shrink-0 transition-transform ${
                            isOpen ? "rotate-180" : ""
                          }`}
                        />
                      </button>
                      {isOpen && (
                        <p className="pb-5 text-[14px] text-[#666666] leading-relaxed max-w-2xl">
                          {item.a}
                        </p>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
