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
    description: "For individual researchers and small clinical teams.",
    cta: "Get Started",
    ctaHref: "/register",
    dark: false,
    features: [
      "Up to 500 records / month",
      "CSV, JSON, plain text",
      "Multilingual PII detection",
      "Basic pseudonymisation",
      "Privacy Passport (basic)",
      "Community support",
    ],
  },
  {
    id: "pro",
    name: "PRO",
    price: { monthly: "₹4,999", annually: "₹3,999" },
    priceSuffix: "/mo",
    description: "For hospitals, diagnostic labs and growing health-tech teams.",
    cta: "Get Started",
    ctaHref: "/register?plan=pro",
    dark: true,
    badge: "MOST POPULAR",
    features: [
      "Unlimited records",
      "All file formats + FHIR R4",
      "Full multilingual detection",
      "Advanced pseudonymisation",
      "Cross-hospital identity linking",
      "Clinical integrity validation",
      "Adversarial attack simulator",
      "Full Privacy Passport + audit",
      "Research network access",
      "Priority support",
    ],
  },
  {
    id: "enterprise",
    name: "ENTERPRISE",
    price: { monthly: "Custom", annually: "Custom" },
    description: "For hospital networks, government health agencies and research consortia.",
    cta: "Contact Us",
    ctaHref: "/contact",
    dark: false,
    features: [
      "Everything in Pro",
      "Custom data retention policies",
      "On-premise deployment",
      "Dedicated support SLA",
      "Multi-org privacy governance",
      "Custom compliance reports",
      "API access + SDK",
      "Audit log export",
    ],
  },
];

export default function PricingPage() {
  const [annual, setAnnual] = useState(true);

  return (
    <div style={{ background: "#F2F2F2", minHeight: "100vh" }}>
      <MarketingNav />

      <div style={{ maxWidth: 1100, margin: "0 auto", padding: "72px 24px 100px" }}>
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
            Pricing Page
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
            Simple, Transparent Pricing
            <br />
            For Your Privacy Needs
          </h1>
          <p
            style={{
              fontSize: 15,
              color: "#666666",
              lineHeight: 1.6,
              maxWidth: 460,
              margin: "0 auto 28px",
            }}
          >
            Protect patient identities, preserve clinical data, and enable secure
            research collaboration — all in one place.
          </p>

          {/* Toggle */}
          <div
            style={{
              display: "inline-flex",
              background: "#FFFFFF",
              border: "1.5px solid #DCDCDC",
              borderRadius: 100,
              padding: 3,
              gap: 2,
            }}
          >
            {[
              { label: "Monthly", val: false },
              { label: "Annually", val: true },
            ].map((opt) => (
              <button
                key={opt.label}
                onClick={() => setAnnual(opt.val)}
                style={{
                  padding: "7px 20px",
                  borderRadius: 100,
                  border: "none",
                  cursor: "pointer",
                  fontSize: 13,
                  fontWeight: 500,
                  background: annual === opt.val ? "#050505" : "transparent",
                  color: annual === opt.val ? "#FFFFFF" : "#555555",
                  display: "flex",
                  alignItems: "center",
                  gap: 6,
                }}
              >
                {opt.label}
                {opt.val && (
                  <span
                    style={{
                      background: "#050505",
                      color: "#FFFFFF",
                      fontSize: 10,
                      padding: "2px 6px",
                      borderRadius: 4,
                      fontWeight: 600,
                      display: annual ? "none" : "inline",
                      border: "1px solid #333",
                    }}
                  >
                    -20%
                  </span>
                )}
              </button>
            ))}
          </div>
        </div>

        {/* Plans grid */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))",
            gap: 20,
            alignItems: "start",
          }}
        >
          {PLANS.map((plan) => (
            <div
              key={plan.id}
              style={{
                position: "relative",
                background: plan.dark ? "#050505" : "#FFFFFF",
                border: `1.5px solid ${plan.dark ? "#050505" : "#DCDCDC"}`,
                borderRadius: 12,
                padding: "32px 28px",
              }}
            >
              {plan.badge && (
                <div
                  style={{
                    position: "absolute",
                    top: -13,
                    left: "50%",
                    transform: "translateX(-50%)",
                    background: "#FFFFFF",
                    border: "1.5px solid #DCDCDC",
                    borderRadius: 100,
                    padding: "3px 14px",
                    fontSize: 10.5,
                    fontWeight: 700,
                    letterSpacing: "0.5px",
                    color: "#050505",
                    whiteSpace: "nowrap",
                  }}
                >
                  {plan.badge}
                </div>
              )}

              <div
                style={{
                  fontSize: 11,
                  fontWeight: 700,
                  letterSpacing: "1.5px",
                  color: plan.dark ? "#777777" : "#777777",
                  marginBottom: 12,
                }}
              >
                {plan.name}
              </div>
              <div
                style={{
                  fontSize: 44,
                  fontWeight: 700,
                  color: plan.dark ? "#FFFFFF" : "#050505",
                  letterSpacing: "-2px",
                  lineHeight: 1,
                  marginBottom: 4,
                }}
              >
                {annual ? plan.price.annually : plan.price.monthly}
                {plan.priceSuffix && (
                  <span style={{ fontSize: 16, fontWeight: 400, letterSpacing: 0 }}>
                    {plan.priceSuffix}
                  </span>
                )}
              </div>
              <p
                style={{
                  fontSize: 13,
                  color: plan.dark ? "#888888" : "#666666",
                  lineHeight: 1.5,
                  marginBottom: 24,
                  minHeight: 40,
                }}
              >
                {plan.description}
              </p>

              <Link
                href={plan.ctaHref}
                style={{
                  display: "block",
                  textAlign: "center",
                  padding: "12px 20px",
                  background: plan.dark ? "#FFFFFF" : "transparent",
                  color: plan.dark ? "#050505" : "#050505",
                  border: `1.5px solid ${plan.dark ? "#FFFFFF" : "#DCDCDC"}`,
                  borderRadius: 7,
                  textDecoration: "none",
                  fontSize: 14,
                  fontWeight: 600,
                  marginBottom: 24,
                }}
              >
                {plan.cta}
              </Link>

              <div
                style={{
                  fontSize: 11,
                  fontWeight: 600,
                  letterSpacing: "0.5px",
                  color: plan.dark ? "#555555" : "#777777",
                  marginBottom: 12,
                  textTransform: "uppercase",
                }}
              >
                Includes:
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {plan.features.map((f) => (
                  <div key={f} style={{ display: "flex", alignItems: "flex-start", gap: 10 }}>
                    <Check
                      size={14}
                      style={{ flexShrink: 0, marginTop: 1, color: plan.dark ? "#FFFFFF" : "#050505" }}
                    />
                    <span
                      style={{
                        fontSize: 13.5,
                        color: plan.dark ? "#CCCCCC" : "#444444",
                        lineHeight: 1.4,
                      }}
                    >
                      {f}
                    </span>
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
