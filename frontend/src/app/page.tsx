import Link from "next/link";
import MarketingNav from "@/components/layout/MarketingNav";

const TRUST_METRICS = [
  {
    value: "0/4",
    label: "Canary leaks",
    caption: "dev/input · 200 files",
    cardClass: "bg-[#090909] text-white border-[#090909]",
    labelClass: "text-[#B5B5B5]",
    captionClass: "text-[#888888]",
  },
  {
    value: "1.00",
    label: "Identity precision",
    caption: "823 records · 0 false merges",
    cardClass: "bg-[#E6E6E6] text-[#090909] border-[#DADADA]",
    labelClass: "text-[#555555]",
    captionClass: "text-[#777777]",
  },
  {
    value: "99.8%",
    label: "Clinical data preserved",
    caption: "4,449 / 4,457 values",
    cardClass: "bg-[#BFBFBF] text-[#090909] border-[#B0B0B0]",
    labelClass: "text-[#333333]",
    captionClass: "text-[#555555]",
  },
  {
    value: "100%",
    label: "Offline, CPU-only",
    caption: "Zero LLMs · Zero cloud calls",
    cardClass: "bg-white text-[#090909] border-[#DADADA]",
    labelClass: "text-[#666666]",
    captionClass: "text-[#888888]",
  },
];

const FEATURES = [
  {
    num: "01",
    title: "Multilingual PII detection",
    desc: "English, Hindi/Devanagari and Hinglish across CSV, TSV, JSON, FHIR R4 and clinical notes. No LLMs.",
  },
  {
    num: "02",
    title: "Cross-hospital identity continuity",
    desc: "Phonetic, transliteration and structural evidence with conservative abstention — zero false merges.",
  },
  {
    num: "03",
    title: "Clinical integrity and re-identification risk",
    desc: "Labs, medicines and FHIR R4 stay intact while k-anonymity and structural uniqueness risks are measured.",
  },
  {
    num: "04",
    title: "Privacy passports and attack simulation",
    desc: "Hash-verified pseudonym manifests, plus 7-vector linkage and canary-recall checks on your output.",
  },
];

export default function HomePage() {
  return (
    <div className="min-h-screen bg-[#F4F4F2] text-[#090909]">
      <MarketingNav />

      {/* Hero Section */}
      <section className="max-w-[1160px] mx-auto px-6 pt-16 sm:pt-24 pb-12">
        <div className="text-[11px] font-semibold uppercase tracking-[0.12em] text-[#666666] mb-5">
          HEALTHCARE DATA PRIVACY INFRASTRUCTURE
        </div>

        <h1 className="font-serif-display text-[48px] sm:text-[68px] lg:text-[84px] leading-[1.02] tracking-[-0.02em] text-[#090909] max-w-4xl">
          What happens in the ward,
          <br />
          <span className="italic text-[#888888]">stays in the ward.</span>
        </h1>

        <div className="mt-10 flex flex-col md:flex-row md:items-end justify-between gap-8">
          <p className="text-[16px] sm:text-[17px] leading-[1.6] text-[#666666] max-w-lg">
            MediLocker protects patient identities while keeping every clinically
            valuable value intact, so hospitals, labs and researchers can finally
            collaborate.
          </p>

          <div className="flex flex-wrap items-center gap-3 shrink-0">
            <Link
              href="/register"
              className="px-6 py-3 rounded-full bg-[#090909] text-white text-[13.5px] font-medium hover:bg-[#222222] transition-colors"
            >
              Get started free
            </Link>
            <Link
              href="/dashboard"
              className="px-6 py-3 rounded-full bg-white border border-[#090909] text-[#090909] text-[13.5px] font-medium hover:bg-[#E6E6E6] transition-colors"
            >
              Open console
            </Link>
          </div>
        </div>
      </section>

      {/* Four Monochrome Trust Metric Cards */}
      <section
        aria-label="Verified Benchmark Metrics"
        className="max-w-[1160px] mx-auto px-6 py-8"
      >
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {TRUST_METRICS.map((m) => (
            <div
              key={m.label}
              title={m.caption}
              className={`rounded-2xl border p-7 flex flex-col justify-between min-h-[164px] ${m.cardClass}`}
            >
              <div className="font-serif-display text-[44px] sm:text-[48px] leading-none tracking-[-0.02em]">
                {m.value}
              </div>
              <div className="mt-6">
                <div className={`text-[13.5px] font-medium ${m.labelClass}`}>
                  {m.label}
                </div>
                <div className={`text-[11px] mt-1 ${m.captionClass}`}>
                  {m.caption}
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Asymmetric Features Section */}
      <section
        id="features"
        className="max-w-[1160px] mx-auto px-6 py-20 sm:py-28"
      >
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-start">
          <div className="lg:col-span-5">
            <h2 className="font-serif-display text-[36px] sm:text-[44px] leading-[1.1] tracking-[-0.015em] text-[#090909]">
              Built to survive a breach, and an audit.
            </h2>
          </div>

          <div className="lg:col-span-7 border-t border-[#DADADA]">
            {FEATURES.map((f) => (
              <div
                key={f.num}
                className="py-6 border-b border-[#DADADA] grid grid-cols-[44px_1fr] gap-4 items-start"
              >
                <span className="font-serif-display text-[17px] text-[#888888] pt-0.5">
                  {f.num}
                </span>
                <div>
                  <h3 className="text-[15.5px] font-semibold text-[#090909]">
                    {f.title}
                  </h3>
                  <p className="text-[13.5px] text-[#666666] mt-1 leading-relaxed">
                    {f.desc}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Final Dark CTA */}
      <section className="max-w-[1160px] mx-auto px-6 pb-16">
        <div className="bg-[#090909] text-white rounded-3xl px-8 sm:px-12 py-12 sm:py-14 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-6">
          <h2 className="font-serif-display text-[32px] sm:text-[40px] leading-tight tracking-[-0.015em]">
            Ready to protect your patients?
          </h2>
          <Link
            href="/register"
            className="inline-flex items-center justify-center px-6 py-3 rounded-full bg-white text-[#090909] text-[13.5px] font-semibold hover:bg-[#E6E6E6] transition-colors shrink-0"
          >
            Start for free
          </Link>
        </div>
      </section>

      {/* Restrained Footer */}
      <footer className="max-w-[1160px] mx-auto px-6 py-8 border-t border-[#E5E5E5] flex flex-col sm:flex-row items-center justify-between gap-4 text-[12px] text-[#888888]">
        <span>© 2026 Yugaantar DevForge</span>
        <span>Fully offline · No LLMs · CPU-only</span>
      </footer>
    </div>
  );
}
