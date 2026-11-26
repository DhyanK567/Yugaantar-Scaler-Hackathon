import Link from "next/link";
import Image from "next/image";
import MarketingNav from "@/components/layout/MarketingNav";
import {
  Shield,
  Network,
  HeartPulse,
  Brain,
  FileKey2,
  Swords,
  ArrowRight,
  CheckCircle2,
} from "lucide-react";

const FEATURES = [
  {
    icon: Shield,
    title: "Multilingual PII Detection",
    desc: "Detects patient identifiers across English, Hindi, Tamil, Telugu, Bengali, Marathi and more using deterministic NLP — no LLMs required.",
  },
  {
    icon: Network,
    title: "Cross-Hospital Identity Continuity",
    desc: "Links patient records across hospitals and diagnostic labs using phonetic, transliteration and structural evidence without false merges.",
  },
  {
    icon: HeartPulse,
    title: "Clinical Integrity Preservation",
    desc: "Lab values, diagnoses, medications and FHIR R4 clinical fields are preserved with 99.8%+ accuracy through every sanitisation pass.",
  },
  {
    icon: Brain,
    title: "Re-identification Risk Analysis",
    desc: "Adversarial red-team simulations measure re-identification risk and quasi-identifier k-anonymity before data leaves your environment.",
  },
  {
    icon: FileKey2,
    title: "Cryptographic Privacy Passports",
    desc: "Every sanitised dataset carries a cryptographically verifiable Privacy Passport with deterministic pseudonym proofs.",
  },
  {
    icon: Swords,
    title: "Adversarial Attack Simulation",
    desc: "Built-in attack simulator tests linkage, singling-out, inference and canary-recall attacks against your sanitised output.",
  },
];

const STATS = [
  { value: "0/4", label: "Canary leaks" },
  { value: "1.00", label: "Identity precision" },
  { value: "99.8%", label: "Clinical data preserved" },
  { value: "100%", label: "Offline · CPU-only" },
];

export default function HomePage() {
  return (
    <div style={{ background: "#F2F2F2", minHeight: "100vh" }}>
      <MarketingNav />

      {/* Hero */}
      <section
        style={{
          maxWidth: 1200,
          margin: "0 auto",
          padding: "80px 24px 60px",
          textAlign: "center",
        }}
      >
        {/* Badge */}
        <div
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 8,
            padding: "6px 14px",
            background: "#FFFFFF",
            border: "1px solid #DCDCDC",
            borderRadius: 100,
            fontSize: 12.5,
            color: "#555555",
            marginBottom: 32,
            fontWeight: 500,
          }}
        >
          <span
            style={{
              width: 6,
              height: 6,
              borderRadius: "50%",
              background: "#050505",
              display: "inline-block",
            }}
          />
          Healthcare Data Privacy Infrastructure
        </div>

        {/* Heading */}
        <h1
          style={{
            fontSize: "clamp(40px, 6vw, 72px)",
            fontWeight: 700,
            lineHeight: 1.08,
            letterSpacing: "-2.5px",
            color: "#050505",
            maxWidth: 800,
            margin: "0 auto 20px",
          }}
        >
          Secure. Private.
          <br />
          Clinically Usable.
        </h1>

        <p
          style={{
            fontSize: 18,
            color: "#555555",
            maxWidth: 540,
            margin: "0 auto 40px",
            lineHeight: 1.6,
            fontWeight: 400,
          }}
        >
          MediLocker protects patient identities while preserving clinically
          valuable medical information — enabling secure collaboration between
          hospitals, labs and research institutions.
        </p>

        {/* CTAs */}
        <div
          style={{
            display: "flex",
            gap: 12,
            justifyContent: "center",
            flexWrap: "wrap",
          }}
        >
          <Link
            href="/register"
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 8,
              padding: "12px 28px",
              background: "#050505",
              color: "#FFFFFF",
              borderRadius: 8,
              textDecoration: "none",
              fontSize: 15,
              fontWeight: 600,
              letterSpacing: "-0.2px",
            }}
          >
            Get Started Free
            <ArrowRight size={16} />
          </Link>
          <Link
            href="/dashboard"
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 8,
              padding: "12px 28px",
              background: "#FFFFFF",
              color: "#050505",
              border: "1.5px solid #DCDCDC",
              borderRadius: 8,
              textDecoration: "none",
              fontSize: 15,
              fontWeight: 500,
            }}
          >
            Open Console
          </Link>
        </div>
      </section>

      {/* Stats bar */}
      <section
        style={{
          background: "#050505",
          padding: "28px 24px",
        }}
      >
        <div
          style={{
            maxWidth: 900,
            margin: "0 auto",
            display: "grid",
            gridTemplateColumns: "repeat(4, 1fr)",
            gap: 24,
            textAlign: "center",
          }}
        >
          {STATS.map((s) => (
            <div key={s.label}>
              <div
                style={{
                  fontSize: 28,
                  fontWeight: 700,
                  color: "#FFFFFF",
                  letterSpacing: "-1px",
                }}
              >
                {s.value}
              </div>
              <div style={{ fontSize: 12, color: "#777777", marginTop: 4 }}>
                {s.label}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Dashboard preview frame */}
      <section
        style={{
          maxWidth: 1100,
          margin: "0 auto",
          padding: "60px 24px 40px",
        }}
      >
        <div
          style={{
            background: "#FFFFFF",
            border: "1.5px solid #DCDCDC",
            borderRadius: 12,
            overflow: "hidden",
          }}
        >
          {/* Window chrome */}
          <div
            style={{
              background: "#F2F2F2",
              borderBottom: "1px solid #DCDCDC",
              padding: "10px 16px",
              display: "flex",
              alignItems: "center",
              gap: 8,
            }}
          >
            {["#E6E6E6", "#E6E6E6", "#E6E6E6"].map((c, i) => (
              <div
                key={i}
                style={{
                  width: 10,
                  height: 10,
                  borderRadius: "50%",
                  background: c,
                  border: "1px solid #DCDCDC",
                }}
              />
            ))}
            <div
              style={{
                flex: 1,
                marginLeft: 8,
                background: "#FFFFFF",
                border: "1px solid #DCDCDC",
                borderRadius: 4,
                padding: "3px 10px",
                fontSize: 11,
                color: "#777777",
                maxWidth: 240,
              }}
            >
              medilocker.app/dashboard
            </div>
          </div>

          {/* Mock dashboard */}
          <div style={{ display: "flex", height: 320 }}>
            {/* Sidebar preview */}
            <div
              style={{
                width: 160,
                borderRight: "1px solid #EEEEEE",
                padding: "16px 12px",
                background: "#FAFAFA",
              }}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 6,
                  marginBottom: 20,
                }}
              >
                <Image
                  src="/medilocker-logo.jpg"
                  alt="ML"
                  width={20}
                  height={20}
                  style={{ borderRadius: "50%" }}
                />
                <span style={{ fontSize: 11, fontWeight: 600, color: "#050505" }}>
                  MediLocker
                </span>
              </div>
              {["Dashboard", "Datasets", "Privacy Engine", "Attack Sim", "Audit"].map(
                (item, i) => (
                  <div
                    key={item}
                    style={{
                      padding: "5px 8px",
                      borderRadius: 4,
                      marginBottom: 2,
                      fontSize: 10.5,
                      color: i === 0 ? "#050505" : "#888888",
                      background: i === 0 ? "#EEEEEE" : "transparent",
                      fontWeight: i === 0 ? 500 : 400,
                    }}
                  >
                    {item}
                  </div>
                )
              )}
            </div>

            {/* Main area preview */}
            <div style={{ flex: 1, padding: 20 }}>
              <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 16, color: "#050505" }}>
                Privacy Dashboard
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 10, marginBottom: 16 }}>
                {[
                  { label: "Files Processed", val: "200" },
                  { label: "PII Detected", val: "0 leaked" },
                  { label: "Clinical Preserved", val: "99.8%" },
                ].map((m) => (
                  <div
                    key={m.label}
                    style={{
                      background: "#F2F2F2",
                      border: "1px solid #E6E6E6",
                      borderRadius: 6,
                      padding: "10px 12px",
                    }}
                  >
                    <div style={{ fontSize: 16, fontWeight: 700, color: "#050505" }}>
                      {m.val}
                    </div>
                    <div style={{ fontSize: 10, color: "#777777", marginTop: 2 }}>
                      {m.label}
                    </div>
                  </div>
                ))}
              </div>
              <div
                style={{
                  background: "#F2F2F2",
                  border: "1px solid #E6E6E6",
                  borderRadius: 6,
                  padding: "10px 12px",
                  fontSize: 10.5,
                  color: "#555555",
                }}
              >
                <div style={{ fontWeight: 500, marginBottom: 6, color: "#050505" }}>
                  Recent Jobs
                </div>
                {["hospital_a_records.csv", "diagnostic_lab_q3.json", "fhir_bundle_001.json"].map(
                  (f) => (
                    <div
                      key={f}
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        padding: "4px 0",
                        borderBottom: "1px solid #ECECEC",
                      }}
                    >
                      <span>{f}</span>
                      <span
                        style={{
                          background: "#050505",
                          color: "#fff",
                          borderRadius: 3,
                          padding: "1px 6px",
                          fontSize: 9,
                          fontWeight: 500,
                        }}
                      >
                        SANITISED
                      </span>
                    </div>
                  )
                )}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section
        id="features"
        style={{ maxWidth: 1100, margin: "0 auto", padding: "40px 24px 80px" }}
      >
        <div style={{ marginBottom: 48, textAlign: "center" }}>
          <div
            style={{
              display: "inline-block",
              fontSize: 11,
              fontWeight: 600,
              letterSpacing: "1px",
              textTransform: "uppercase",
              color: "#777777",
              marginBottom: 12,
            }}
          >
            Capabilities
          </div>
          <h2
            style={{
              fontSize: "clamp(28px, 4vw, 44px)",
              fontWeight: 700,
              letterSpacing: "-1.5px",
              color: "#050505",
              margin: 0,
            }}
          >
            Everything your privacy
            <br />
            infrastructure needs
          </h2>
        </div>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))",
            gap: 20,
          }}
        >
          {FEATURES.map((f) => {
            const Icon = f.icon;
            return (
              <div
                key={f.title}
                style={{
                  background: "#FFFFFF",
                  border: "1.5px solid #DCDCDC",
                  borderRadius: 10,
                  padding: "28px 24px",
                  transition: "border-color 0.15s",
                }}
              >
                <div
                  style={{
                    width: 36,
                    height: 36,
                    background: "#F2F2F2",
                    borderRadius: 8,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    marginBottom: 16,
                  }}
                >
                  <Icon size={18} strokeWidth={1.5} color="#050505" />
                </div>
                <div
                  style={{
                    fontSize: 15,
                    fontWeight: 600,
                    color: "#050505",
                    marginBottom: 8,
                    letterSpacing: "-0.3px",
                  }}
                >
                  {f.title}
                </div>
                <p
                  style={{
                    fontSize: 13.5,
                    color: "#666666",
                    lineHeight: 1.6,
                    margin: 0,
                  }}
                >
                  {f.desc}
                </p>
              </div>
            );
          })}
        </div>
      </section>

      {/* CTA Banner */}
      <section
        style={{
          background: "#050505",
          padding: "60px 24px",
          textAlign: "center",
        }}
      >
        <div style={{ maxWidth: 600, margin: "0 auto" }}>
          <h2
            style={{
              fontSize: "clamp(28px, 4vw, 40px)",
              fontWeight: 700,
              color: "#FFFFFF",
              letterSpacing: "-1.5px",
              marginBottom: 16,
            }}
          >
            Ready to protect your patients?
          </h2>
          <p
            style={{
              fontSize: 15,
              color: "#888888",
              marginBottom: 32,
              lineHeight: 1.6,
            }}
          >
            Start processing healthcare data with zero PII leakage, full
            clinical integrity and cryptographic audit trails.
          </p>
          <div style={{ display: "flex", gap: 12, justifyContent: "center", flexWrap: "wrap" }}>
            <Link
              href="/register"
              style={{
                padding: "12px 28px",
                background: "#FFFFFF",
                color: "#050505",
                borderRadius: 8,
                textDecoration: "none",
                fontSize: 15,
                fontWeight: 600,
              }}
            >
              Start for Free
            </Link>
            <Link
              href="/pricing"
              style={{
                padding: "12px 28px",
                background: "transparent",
                color: "#FFFFFF",
                border: "1.5px solid #333333",
                borderRadius: 8,
                textDecoration: "none",
                fontSize: 15,
                fontWeight: 500,
              }}
            >
              View Pricing
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer
        style={{
          background: "#FFFFFF",
          borderTop: "1px solid #DCDCDC",
          padding: "32px 24px",
        }}
      >
        <div
          style={{
            maxWidth: 1100,
            margin: "0 auto",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            flexWrap: "wrap",
            gap: 16,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <Image
              src="/medilocker-logo.jpg"
              alt="MediLocker"
              width={22}
              height={22}
              style={{ borderRadius: "50%" }}
            />
            <span style={{ fontSize: 13, fontWeight: 600, color: "#050505" }}>
              MediLocker
            </span>
            <span style={{ fontSize: 12, color: "#AAAAAA", marginLeft: 8 }}>
              © 2024 Yugaantar DevForge
            </span>
          </div>
          <div style={{ display: "flex", gap: 24 }}>
            {[
              { label: "Pricing", href: "/pricing" },
              { label: "FAQ", href: "/faq" },
              { label: "Console", href: "/dashboard" },
            ].map((l) => (
              <Link
                key={l.href}
                href={l.href}
                style={{ fontSize: 13, color: "#777777", textDecoration: "none" }}
              >
                {l.label}
              </Link>
            ))}
          </div>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 6,
              fontSize: 11.5,
              color: "#AAAAAA",
            }}
          >
            <CheckCircle2 size={12} />
            Fully offline · No LLMs · CPU-only
          </div>
        </div>
      </footer>
    </div>
  );
}
