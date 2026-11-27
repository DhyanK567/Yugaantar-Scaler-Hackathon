"use client";

import { useState } from "react";
import { HelpCircle } from "lucide-react";

export const PLAIN_LANGUAGE_TERMS: Record<string, string> = {
  PII: "Personally identifiable information — details such as names, phone numbers, or IDs that could reveal who a patient is.",
  Pseudonymisation:
    "Replacing a patient's real identity with a consistent protected reference so records stay linked without exposing who they are.",
  "Identity precision":
    "Of the patient matches made across records, how many were truly the same person (avoiding false merges).",
  "Identity recall":
    "Of the patient matches that should have been found across hospitals, how many were successfully linked.",
  "Clinical fidelity":
    "How much of the original medical information (medications, dosages, vitals, labs, diagnoses) remained completely unchanged.",
  "Quasi-identifiers":
    "Information such as age band, visit dates, or rare diagnoses that looks harmless alone but can reveal identity when combined.",
  Canary:
    "A hidden synthetic test identifier planted in test data to verify that private information never leaks into the output.",
  "Privacy Passport":
    "A cryptographic verification record that proves the output files have not been tampered with and records the release decision.",
};

interface InfoTermProps {
  term: keyof typeof PLAIN_LANGUAGE_TERMS | string;
  explanation?: string;
}

export function InfoTerm({ term, explanation }: InfoTermProps) {
  const [open, setOpen] = useState(false);
  const text = explanation || PLAIN_LANGUAGE_TERMS[term] || "";
  if (!text) return <span>{term}</span>;

  return (
    <span className="relative inline-flex items-center gap-1 align-middle">
      <span>{term}</span>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        onBlur={() => setTimeout(() => setOpen(false), 180)}
        aria-label={`Explain ${term}`}
        title={text}
        className="inline-flex items-center justify-center text-[#888888] hover:text-[#090909] focus:outline-none"
      >
        <HelpCircle size={13} />
      </button>
      {open && (
        <span
          role="tooltip"
          className="absolute left-0 top-full mt-1.5 z-40 w-64 p-2.5 rounded-xl bg-[#090909] text-white text-[11.5px] leading-relaxed font-normal shadow-lg"
        >
          {text}
        </span>
      )}
    </span>
  );
}
