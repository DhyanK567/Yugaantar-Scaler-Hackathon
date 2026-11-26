"use client";

import { useEffect, useState } from "react";
import { api, type JobRecord, type SettingsData } from "@/lib/api";
import { PageHeader } from "@/components/ui/PageHeader";
import { EmptyState, ErrorState } from "@/components/ui/StatePanels";
import { StatusBadge } from "@/components/dashboard/StatusBadge";

const ENGINE_STAGES = [
  "01. Input validation",
  "02. Secure ingestion",
  "03. Format detection",
  "04. Multilingual PII detection",
  "05. Clinical preservation",
  "06. Identity resolution",
  "07. Pseudonymisation",
  "08. Re-identification risk analysis",
  "09. Security validation",
  "10. Release decision",
];

export default function PrivacyEnginePage() {
  const [jobs, setJobs] = useState<JobRecord[]>([]);
  const [settings, setSettings] = useState<SettingsData | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([api.jobs(), api.settings()])
      .then(([j, s]) => {
        setJobs(j);
        setSettings(s);
      })
      .catch((e) => setError(e.message));
  }, []);

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="03 · DETERMINISTIC PIPELINE"
        title="Privacy Engine"
        subtitle="Offline, CPU-only sanitisation workflow and persistent processing job history."
      />

      {error && <ErrorState message={error} />}

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: "Execution Mode", value: "CPU-Only", sub: "Air-gapped · Zero LLMs" },
          {
            label: "RAKSHA_SECRET",
            value: settings ? (settings.raksha_secret_set ? "Configured" : "Fallback") : "—",
            sub: "HMAC-SHA256 pseudonym key",
          },
          { label: "Total Jobs", value: String(jobs.length), sub: "Persistent SQLite history" },
          {
            label: "Multilingual NLP",
            value: settings ? (settings.multilingual_enabled ? "Enabled" : "Disabled") : "—",
            sub: `Output: ${settings?.output_format ?? "—"}`,
          },
        ].map((card) => (
          <div key={card.label} className="bg-white border border-[#DADADA] rounded-2xl p-5">
            <div className="text-[11px] font-semibold uppercase tracking-[0.08em] text-[#888888] mb-2">
              {card.label}
            </div>
            <div className="font-serif-display text-[28px] leading-none text-[#090909]">
              {card.value}
            </div>
            <div className="text-[12px] text-[#666666] mt-2">{card.sub}</div>
          </div>
        ))}
      </div>

      {/* 10-Stage Workflow */}
      <div className="bg-white border border-[#DADADA] rounded-2xl p-6">
        <h2 className="text-[15px] font-semibold text-[#090909] mb-4">
          10-Stage Deterministic Processing Architecture
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
          {ENGINE_STAGES.map((stage) => (
            <div
              key={stage}
              className="px-3.5 py-3 rounded-xl bg-[#F4F4F2] border border-[#E5E5E5] text-[12.5px] font-medium text-[#090909]"
            >
              {stage}
            </div>
          ))}
        </div>
      </div>

      {/* Jobs Table */}
      <div className="bg-white border border-[#DADADA] rounded-2xl overflow-hidden">
        <div className="px-6 py-4 border-b border-[#E5E5E5]">
          <h2 className="text-[15px] font-semibold text-[#090909]">Processing Jobs</h2>
        </div>
        {jobs.length === 0 ? (
          <div className="p-6">
            <EmptyState
              title="No processing jobs recorded"
              description="Upload a dataset to execute the 10-stage offline privacy engine."
            />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-[#E5E5E5] bg-[#F4F4F2]/60">
                  {["Job ID", "Dataset", "Status", "Release", "Files", "Records", "Created"].map((h) => (
                    <th key={h} className="px-5 py-3 text-[11px] font-semibold uppercase tracking-[0.05em] text-[#666666]">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-[#E5E5E5]">
                {jobs.map((j) => (
                  <tr key={j.id} className="hover:bg-[#F4F4F2]/40">
                    <td className="px-5 py-3 text-[12px] font-mono text-[#090909]">{j.id}</td>
                    <td className="px-5 py-3 text-[13px] text-[#090909]">{j.dataset_name || j.input_name || "—"}</td>
                    <td className="px-5 py-3"><StatusBadge status={j.status} /></td>
                    <td className="px-5 py-3"><StatusBadge status={j.release_decision || "PENDING"} /></td>
                    <td className="px-5 py-3 text-[13px]">{j.files_total ?? 0}</td>
                    <td className="px-5 py-3 text-[13px]">{j.records_processed ?? 0}</td>
                    <td className="px-5 py-3 text-[12px] text-[#666666] whitespace-nowrap">
                      {new Date(j.created_at * 1000).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
