"use client";
import { useState } from "react";
import MarketingNav from "@/components/layout/MarketingNav";
import { ChevronDown } from "lucide-react";

const FAQS = [
  {
    category: "GETTING STARTED",
    questions: [
      {
        q: "What is MediLocker?",
        a: "MediLocker is a healthcare data privacy infrastructure platform. It sanitises patient records, detects personally identifiable information (PII) across multiple Indian and international languages, links patient identities across hospitals without false merges, and preserves clinically meaningful data through every transformation.",
      },
      {
        q: "Does MediLocker use AI or cloud services?",
        a: "No. MediLocker is entirely offline and CPU-only. It uses deterministic NLP, phonetic matching, cryptographic pseudonymisation and rules-based detection — no LLMs, no hosted AI APIs, no internet dependency during processing.",
      },
      {
        q: "What file formats does MediLocker support?",
        a: "MediLocker processes CSV, TSV, JSON, FHIR R4 JSON bundles, plain text and mixed archives. It handles structured, semi-structured and free-text clinical records.",
      },
    ],
  },
  {
    category: "PRIVACY & SECURITY",
    questions: [
      {
        q: "What languages does PII detection cover?",
        a: "MediLocker detects patient identifiers across English, Hindi, Tamil, Telugu, Bengali, Marathi, Gujarati, Kannada, Malayalam, Punjabi and Odia — including transliterations and mixed-script text.",
      },
      {
        q: "How does pseudonymisation work?",
        a: "Patient names and identifiers are replaced with cryptographic pseudonyms derived from a secret key (RAKSHA_SECRET) using HMAC-SHA256. The same patient always receives the same pseudonym within a session, but different secrets produce different pseudonyms — making reversal impossible without the key.",
      },
      {
        q: "How are canary values handled?",
        a: "MediLocker detects embedded canary tokens (synthetic tracers used by evaluators to verify data never escapes). In testing, 0/4 canary values leaked through sanitised output.",
      },
    ],
  },
  {
    category: "CLINICAL INTEGRITY",
    questions: [
      {
        q: "Will sanitisation break clinical values?",
        a: "No. Lab values, medication dosages, diagnoses, LOINC codes, SNOMED codes and FHIR R4 clinical fields are preserved with 99.8%+ accuracy. MediLocker distinguishes between identifiers (which must be removed) and clinical measurements (which must be kept).",
      },
      {
        q: "What is the Privacy Passport?",
        a: "Every sanitised dataset carries a cryptographically verifiable Privacy Passport — a signed manifest that records what was detected, what was replaced, and what clinical values were preserved. It provides an auditable chain of evidence for research ethics boards.",
      },
    ],
  },
  {
    category: "IDENTITY & PERFORMANCE",
    questions: [
      {
        q: "How does cross-hospital identity linking work?",
        a: "MediLocker uses a multi-evidence blocking and clustering approach: it matches on MRN, UHID, ABHA identifiers, name phonetics (Soundex, Double Metaphone), date of birth, gender and contact details. Conservative thresholds prevent false merges. Precision is 1.00 (no false merges) with F0.5 ≥ 0.93.",
      },
      {
        q: "What are the hardware requirements?",
        a: "MediLocker runs on 2 CPUs, 4 GB RAM. It processes 200 files and 820+ records in under 15 minutes. Streaming ingestion and batched identity resolution keep memory usage bounded even for large datasets.",
      },
    ],
  },
];

function FAQItem({ q, a }: { q: string; a: string }) {
  const [open, setOpen] = useState(false);
  return (
    <div
      style={{
        borderBottom: "1px solid #E6E6E6",
        cursor: "pointer",
      }}
      onClick={() => setOpen(!open)}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "18px 0",
          gap: 16,
        }}
      >
        <span style={{ fontSize: 15, fontWeight: 500, color: "#050505", lineHeight: 1.4 }}>
          {q}
        </span>
        <ChevronDown
          size={18}
          style={{
            flexShrink: 0,
            color: "#777777",
            transform: open ? "rotate(180deg)" : "rotate(0deg)",
            transition: "transform 0.2s",
          }}
        />
      </div>
      {open && (
        <div
          style={{
            paddingBottom: 20,
            fontSize: 14,
            color: "#555555",
            lineHeight: 1.7,
          }}
        >
          {a}
        </div>
      )}
    </div>
  );
}

export default function FAQPage() {
  return (
    <div style={{ background: "#F2F2F2", minHeight: "100vh" }}>
      <MarketingNav />

      <div style={{ maxWidth: 900, margin: "0 auto", padding: "72px 24px 100px" }}>
        {/* Header */}
        <div style={{ marginBottom: 56, textAlign: "center" }}>
          <div
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 8,
              padding: "5px 14px",
              background: "#FFFFFF",
              border: "1px solid #DCDCDC",
              borderRadius: 100,
              fontSize: 12,
              color: "#555555",
              fontWeight: 500,
              marginBottom: 20,
            }}
          >
            Frequently Asked Questions
          </div>
          <h1
            style={{
              fontSize: "clamp(32px, 5vw, 56px)",
              fontWeight: 700,
              letterSpacing: "-2px",
              color: "#050505",
              margin: "0 0 16px",
            }}
          >
            Get Quick Answers To
            <br />
            Common Questions
          </h1>
          <p style={{ fontSize: 15, color: "#666666", lineHeight: 1.6, margin: 0 }}>
            Find solutions, explore resources, and resolve issues faster.
          </p>
        </div>

        {/* FAQ layout */}
        <div style={{ display: "flex", gap: 48, alignItems: "flex-start" }}>
          {/* Sidebar card */}
          <div
            style={{
              flexShrink: 0,
              width: 240,
              background: "#FFFFFF",
              border: "1.5px solid #DCDCDC",
              borderRadius: 10,
              padding: 24,
              position: "sticky",
              top: 80,
            }}
          >
            <div
              style={{
                fontSize: 11,
                fontWeight: 600,
                letterSpacing: "1px",
                textTransform: "uppercase",
                color: "#777777",
                marginBottom: 12,
              }}
            >
              Support
            </div>
            <div
              style={{
                fontSize: 15,
                fontWeight: 600,
                color: "#050505",
                marginBottom: 8,
              }}
            >
              MediLocker Privacy Team
            </div>
            <div style={{ fontSize: 13, color: "#666666", lineHeight: 1.5, marginBottom: 16 }}>
              Here to help you configure your perfect privacy pipeline.
            </div>
            <div
              style={{
                width: "100%",
                height: 1,
                background: "#EEEEEE",
                marginBottom: 16,
              }}
            />
            {FAQS.map((section) => (
              <a
                key={section.category}
                href={`#${section.category}`}
                style={{
                  display: "block",
                  fontSize: 12,
                  color: "#555555",
                  textDecoration: "none",
                  marginBottom: 8,
                  fontWeight: 500,
                }}
              >
                {section.category}
              </a>
            ))}
          </div>

          {/* Questions */}
          <div style={{ flex: 1 }}>
            {FAQS.map((section) => (
              <div key={section.category} id={section.category} style={{ marginBottom: 48 }}>
                <div
                  style={{
                    fontSize: 11,
                    fontWeight: 600,
                    letterSpacing: "1px",
                    textTransform: "uppercase",
                    color: "#777777",
                    marginBottom: 16,
                    paddingBottom: 12,
                    borderBottom: "1px solid #DCDCDC",
                  }}
                >
                  {section.category}
                </div>
                {section.questions.map((item) => (
                  <FAQItem key={item.q} {...item} />
                ))}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
