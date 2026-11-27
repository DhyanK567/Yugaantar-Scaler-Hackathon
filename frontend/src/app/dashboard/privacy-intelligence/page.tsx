"use client";

import { useCallback, useEffect, useState } from "react";
import { api, type PrivacyIntelligence } from "@/lib/api";
import { PageHeader } from "@/components/ui/PageHeader";
import { EmptyState, ErrorState } from "@/components/ui/StatePanels";
import { StatusBadge } from "@/components/dashboard/StatusBadge";
import { RefreshCw, ShieldCheck, Activity, Swords, ArrowRightLeft, CheckCircle2 } from "lucide-react";

function fmtPct(val?: number | null): string {
  if (val === null || val === undefined) return "NOT MEASURED";
  return `${(val * 100).toFixed(1)}%`;
}

export default function PrivacyIntelligencePage() {
  const [intel, setIntel] = useState<PrivacyIntelligence | null>(null);
  const [selectedJobId, setSelectedJobId] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState("");

  const loadIntelligence = useCallback(async (jobId?: string) => {
    setLoading(true);
    setError("");
    try {
      const data = await api.privacyIntelligence(jobId || undefined);
      setIntel(data);
      if (data.selected_job_id && !jobId) {
        setSelectedJobId(data.selected_job_id);
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const id = setTimeout(() => {
      void loadIntelligence();
    }, 0);
    return () => clearTimeout(id);
  }, [loadIntelligence]);

  const measured = intel?.status === "MEASURED";
  const jobs = intel?.jobs ?? [];
  const cf = intel?.clinical_fidelity;
  const cd = intel?.clinical_drift;
  const ao = intel?.attack_overview;
  const ba = intel?.before_after;
  const rr = intel?.release_readiness;

  const maxDriftCount = Math.max(
    1,
    ...(cd?.categories ?? []).map((c) => Math.max(c.input_count, c.output_count))
  );

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="04 · RISK & LEAKAGE TELEMETRY"
        title="Privacy Intelligence"
        subtitle="Visual proof of PII removal, clinical fidelity preservation, clinical drift analysis, and adversarial defence."
      />

      {/* Job Selector & Refresh Bar */}
      <div className="bg-white border border-[#DADADA] rounded-2xl p-4 flex flex-wrap items-center justify-between gap-4">
        <div className="flex flex-wrap items-center gap-3">
          <label className="text-[12px] font-semibold uppercase tracking-[0.06em] text-[#666666]">
            Dataset Run
          </label>
          <select
            value={selectedJobId}
            onChange={(e) => {
              const next = e.target.value;
              setSelectedJobId(next);
              loadIntelligence(next);
            }}
            disabled={jobs.length === 0 || loading}
            className="px-3 py-2 rounded-lg border border-[#DADADA] bg-[#F9F9F8] text-[13px] text-[#090909] min-w-[260px]"
          >
            {jobs.length === 0 ? (
              <option value="">No processing jobs recorded</option>
            ) : (
              jobs.map((j) => (
                <option key={j.id} value={j.id}>
                  {j.dataset_name || "Dataset"} · {j.id} ({j.release_decision})
                </option>
              ))
            )}
          </select>
        </div>
        <div className="flex items-center gap-4">
          {intel?.last_updated && (
            <span className="text-[12px] text-[#666666]">
              Last updated: {new Date(intel.last_updated * 1000).toLocaleString()}
            </span>
          )}
          <button
            type="button"
            onClick={() => loadIntelligence(selectedJobId || undefined)}
            disabled={loading}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-[#090909] text-white text-[12px] font-medium hover:bg-[#222222] disabled:opacity-50"
          >
            <RefreshCw size={13} className={loading ? "animate-spin" : ""} />
            <span>{loading ? "Refreshing..." : "Refresh"}</span>
          </button>
        </div>
      </div>

      {error && <ErrorState message={error} />}

      {/* Top Dark KPI Banner */}
      <div className="bg-[#090909] text-white rounded-2xl p-6 sm:p-7 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        <div>
          <div className="text-[10.5px] font-semibold uppercase tracking-[0.08em] text-[#888888] mb-1.5">
            Assessment Status
          </div>
          <div className="font-serif-display text-[28px] leading-none">
            {intel?.status ?? (loading ? "LOADING" : "NOT_MEASURED")}
          </div>
        </div>
        <div>
          <div className="text-[10.5px] font-semibold uppercase tracking-[0.08em] text-[#888888] mb-1.5">
            Total PII Detected
          </div>
          <div className="font-serif-display text-[28px] leading-none">
            {measured ? intel.total_pii_detected : "Not measured"}
          </div>
        </div>
        <div>
          <div className="text-[10.5px] font-semibold uppercase tracking-[0.08em] text-[#888888] mb-1.5">
            Residual Leakage
          </div>
          <div className="font-serif-display text-[28px] leading-none">
            {measured ? intel.total_residual_leakage : "Not measured"}
          </div>
        </div>
        <div>
          <div className="text-[10.5px] font-semibold uppercase tracking-[0.08em] text-[#888888] mb-1.5">
            Canary Containment
          </div>
          <div className="font-serif-display text-[28px] leading-none">
            {intel?.canary_status ?? "NOT_RUN"}
          </div>
        </div>
      </div>

      {/* Dataset Release Readiness & Privacy Before vs After */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <div className="bg-white border border-[#DADADA] rounded-2xl p-6 space-y-4">
          <div className="flex items-center justify-between border-b border-[#E5E5E5] pb-3">
            <div className="flex items-center gap-2">
              <CheckCircle2 size={16} className="text-[#090909]" />
              <h2 className="text-[15px] font-semibold text-[#090909]">Dataset Release Readiness</h2>
            </div>
            <StatusBadge status={rr?.status ?? "NOT_MEASURED"} />
          </div>
          {!rr || rr.status === "NOT_MEASURED" ? (
            <div className="text-[13px] text-[#666666]">
              NOT MEASURED — Select or run a dataset job to evaluate release readiness.
            </div>
          ) : (
            <div className="space-y-2.5">
              <div className="text-[12.5px] text-[#666666]">
                Gate Decision: <span className="font-semibold text-[#090909]">{rr.decision}</span>
              </div>
              <ul className="space-y-1.5 text-[12.5px] text-[#333333] list-disc pl-5">
                {rr.reasons.map((r, i) => (
                  <li key={i}>{r}</li>
                ))}
              </ul>
            </div>
          )}
        </div>

        <div className="bg-white border border-[#DADADA] rounded-2xl p-6 space-y-4">
          <div className="flex items-center justify-between border-b border-[#E5E5E5] pb-3">
            <div className="flex items-center gap-2">
              <ArrowRightLeft size={16} className="text-[#090909]" />
              <h2 className="text-[15px] font-semibold text-[#090909]">Privacy Before vs After</h2>
            </div>
            <StatusBadge status={ba?.status ?? "NOT_MEASURED"} />
          </div>
          {!ba || ba.status === "NOT_MEASURED" ? (
            <div className="text-[13px] text-[#666666]">NOT MEASURED — No assessment metrics for selected job.</div>
          ) : (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="bg-[#F4F4F2] border border-[#E5E5E5] rounded-xl p-3">
                <div className="text-[10px] font-semibold uppercase text-[#666666]">Before: PII Found</div>
                <div className="font-serif-display text-[22px] text-[#090909] mt-1">
                  {ba.before_pii_detected ?? 0}
                </div>
              </div>
              <div className="bg-[#ECF3EC] border border-[#C6DBC7] rounded-xl p-3">
                <div className="text-[10px] font-semibold uppercase text-[#1E4620]">After: Residual</div>
                <div className="font-serif-display text-[22px] text-[#1E4620] mt-1">
                  {ba.after_residual_leakage ?? 0}
                </div>
              </div>
              <div className="bg-[#F4F4F2] border border-[#E5E5E5] rounded-xl p-3">
                <div className="text-[10px] font-semibold uppercase text-[#666666]">Canaries Planted</div>
                <div className="font-serif-display text-[22px] text-[#090909] mt-1">
                  {ba.canary_planted ?? 0}
                </div>
              </div>
              <div className="bg-[#F4F4F2] border border-[#E5E5E5] rounded-xl p-3">
                <div className="text-[10px] font-semibold uppercase text-[#666666]">Canary Leaks</div>
                <div className="font-serif-display text-[22px] text-[#090909] mt-1">
                  {ba.canary_leaks ?? 0}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Clinical Fidelity Overview */}
      <div className="bg-white border border-[#DADADA] rounded-2xl p-6 space-y-4">
        <div className="flex items-center justify-between border-b border-[#E5E5E5] pb-3">
          <div className="flex items-center gap-2">
            <Activity size={16} className="text-[#090909]" />
            <div>
              <h2 className="text-[15px] font-semibold text-[#090909]">Clinical Fidelity Overview</h2>
              <p className="text-[12px] text-[#666666]">
                Preservation of medications, dosages, lab values, vitals, and FHIR R4 structural integrity.
              </p>
            </div>
          </div>
          <StatusBadge status={cf?.status ?? "NOT_MEASURED"} />
        </div>
        {!cf || cf.status === "NOT_MEASURED" ? (
          <div className="text-[13px] text-[#666666]">NOT MEASURED — Run a dataset job to compute clinical fidelity.</div>
        ) : (
          <div className="space-y-4">
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
              {[
                { label: "Expected Values", val: cf.expected_values ?? 0 },
                { label: "Preserved Values", val: cf.preserved_values ?? 0 },
                { label: "Modified Values", val: cf.modified_values ?? 0 },
                { label: "Missing Values", val: cf.missing_values ?? 0 },
                { label: "Exact Fidelity", val: cf.exact_fidelity_pct != null ? `${cf.exact_fidelity_pct}%` : "NOT MEASURED" },
              ].map((m) => (
                <div key={m.label} className="bg-[#F4F4F2] border border-[#E5E5E5] rounded-xl p-3">
                  <div className="text-[10px] font-semibold uppercase tracking-[0.05em] text-[#666666]">{m.label}</div>
                  <div className="font-serif-display text-[22px] text-[#090909] mt-1">{m.val}</div>
                </div>
              ))}
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 text-[12px]">
              <div className="border border-[#E5E5E5] rounded-xl p-3">
                <div className="text-[#666666]">Lab Integrity</div>
                <div className="font-semibold text-[#090909] mt-0.5">{fmtPct(cf.lab_integrity)}</div>
              </div>
              <div className="border border-[#E5E5E5] rounded-xl p-3">
                <div className="text-[#666666]">Medication Integrity</div>
                <div className="font-semibold text-[#090909] mt-0.5">{fmtPct(cf.medication_integrity)}</div>
              </div>
              <div className="border border-[#E5E5E5] rounded-xl p-3">
                <div className="text-[#666666]">Dosage Integrity</div>
                <div className="font-semibold text-[#090909] mt-0.5">{fmtPct(cf.dosage_integrity)}</div>
              </div>
              <div className="border border-[#E5E5E5] rounded-xl p-3">
                <div className="text-[#666666]">Vital Integrity</div>
                <div className="font-semibold text-[#090909] mt-0.5">{fmtPct(cf.vital_integrity)}</div>
              </div>
              <div className="border border-[#E5E5E5] rounded-xl p-3">
                <div className="text-[#666666]">FHIR R4 ({cf.fhir_bundles_valid ?? 0}/{cf.fhir_bundles_checked ?? 0})</div>
                <div className="font-semibold text-[#090909] mt-0.5">{cf.fhir_integrity ?? "NOT_MEASURED"}</div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Clinical Drift Visualisation */}
      <div className="bg-white border border-[#DADADA] rounded-2xl p-6 space-y-4">
        <div className="flex items-center justify-between border-b border-[#E5E5E5] pb-3">
          <div>
            <h2 className="text-[15px] font-semibold text-[#090909]">Clinical Drift Visualisation</h2>
            <p className="text-[12px] text-[#666666]">
              Input vs sanitised output counts by clinical category. Categories with zero detections are explicitly marked NOT_MEASURED.
            </p>
          </div>
          <StatusBadge status={cd?.status ?? "NOT_MEASURED"} />
        </div>
        {!cd || cd.status === "NOT_MEASURED" || cd.categories.length === 0 ? (
          <div className="text-[13px] text-[#666666]">NOT MEASURED — No category-level clinical drift data available for this run.</div>
        ) : (
          <div className="space-y-3">
            {cd.categories.map((cat) => {
              const inPct = Math.round((cat.input_count / maxDriftCount) * 100);
              const outPct = Math.round((cat.output_count / maxDriftCount) * 100);
              return (
                <div key={cat.key} className="border border-[#E5E5E5] rounded-xl p-3.5 space-y-2">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="text-[13px] font-semibold text-[#090909]">{cat.label}</span>
                    <div className="flex items-center gap-3 text-[11.5px] text-[#666666]">
                      <span>Input: {cat.input_count}</span>
                      <span>Output: {cat.output_count}</span>
                      <span>Modified: {cat.modified_count}</span>
                      <span>Missing: {cat.missing_count}</span>
                      <StatusBadge status={cat.status === "PRESERVED" ? "PASS" : cat.status === "DRIFT_DETECTED" ? "WARNING" : "NOT_MEASURED"} />
                    </div>
                  </div>
                  <div className="space-y-1">
                    <div className="flex items-center gap-2 text-[11px] text-[#666666]">
                      <span className="w-12">Input</span>
                      <div className="flex-1 h-2 bg-[#F4F4F2] rounded-full overflow-hidden">
                        <div className="h-full bg-[#090909]" style={{ width: `${inPct}%` }} />
                      </div>
                    </div>
                    <div className="flex items-center gap-2 text-[11px] text-[#666666]">
                      <span className="w-12">Output</span>
                      <div className="flex-1 h-2 bg-[#F4F4F2] rounded-full overflow-hidden">
                        <div
                          className={`h-full ${cat.drift_detected ? "bg-[#B45309]" : "bg-[#1E4620]"}`}
                          style={{ width: `${outPct}%` }}
                        />
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Attack Simulation Overview */}
      <div className="bg-white border border-[#DADADA] rounded-2xl p-6 space-y-4">
        <div className="flex items-center justify-between border-b border-[#E5E5E5] pb-3">
          <div className="flex items-center gap-2">
            <Swords size={16} className="text-[#090909]" />
            <div>
              <h2 className="text-[15px] font-semibold text-[#090909]">Attack Simulation Overview</h2>
              <p className="text-[12px] text-[#666666]">
                Re-identification attack vectors evaluated against sanitised output (never fabricated).
              </p>
            </div>
          </div>
          <StatusBadge status={ao?.status ?? "NOT_EXECUTED"} />
        </div>
        {!ao || ao.status === "NOT_EXECUTED" ? (
          <div className="text-[13px] text-[#666666]">
            NOT EXECUTED — Run an attack simulation on this job from the Attack Simulator page to view vector outcomes.
          </div>
        ) : (
          <div className="space-y-4">
            <div className="grid grid-cols-2 sm:grid-cols-6 gap-3">
              {[
                { label: "Total Vectors", val: ao.total },
                { label: "Blocked", val: ao.blocked },
                { label: "Exposed", val: ao.exposed },
                { label: "Not Executed", val: ao.not_executed },
                { label: "Failed", val: ao.failed },
                { label: "Risk Score", val: ao.risk_score != null ? `${ao.risk_score}%` : "N/A" },
              ].map((cell) => (
                <div key={cell.label} className="bg-[#F4F4F2] border border-[#E5E5E5] rounded-xl p-3">
                  <div className="text-[10px] font-semibold uppercase text-[#666666]">{cell.label}</div>
                  <div className="font-serif-display text-[22px] text-[#090909] mt-1">{cell.val}</div>
                </div>
              ))}
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-[#E5E5E5] bg-[#F4F4F2]/60">
                    {["Vector", "Outcome", "Matched Records", "Risk Score"].map((h) => (
                      <th key={h} className="px-4 py-2.5 text-[11px] font-semibold uppercase text-[#666666]">
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#E5E5E5]">
                  {ao.strategies.map((s, idx) => (
                    <tr key={idx}>
                      <td className="px-4 py-2.5 text-[12.5px] font-medium text-[#090909]">{s.strategy}</td>
                      <td className="px-4 py-2.5"><StatusBadge status={s.status} /></td>
                      <td className="px-4 py-2.5 text-[12.5px]">{s.matched_records}</td>
                      <td className="px-4 py-2.5 text-[12.5px]">{s.risk_score}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {/* Dataset Privacy Risk Map */}
      <div className="bg-white border border-[#DADADA] rounded-2xl p-6">
        <div className="flex items-center justify-between border-b border-[#E5E5E5] pb-3 mb-4">
          <div className="flex items-center gap-2">
            <ShieldCheck size={16} className="text-[#090909]" />
            <div>
              <h2 className="text-[15px] font-semibold text-[#090909]">Dataset Privacy Risk Map</h2>
              <p className="text-[12px] text-[#666666]">
                Record-level quasi-identifier risk distribution without exposing original patient records.
              </p>
            </div>
          </div>
          <StatusBadge status={intel?.risk_map?.release_decision ?? "NOT_MEASURED"} />
        </div>
        {!intel?.risk_map ? (
          <div className="text-[13px] text-[#666666]">NOT_MEASURED — Run a dataset job to populate the risk map.</div>
        ) : (
          <div className="space-y-4">
            <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3">
              {[
                { label: "LOW", val: intel.risk_map.low },
                { label: "MODERATE", val: intel.risk_map.moderate },
                { label: "HIGH", val: intel.risk_map.high },
                { label: "CRITICAL", val: intel.risk_map.critical },
                { label: "ASSESSED", val: intel.risk_map.total_assessed },
                { label: "MITIGATED", val: intel.risk_map.requiring_mitigation },
                { label: "BLOCKED", val: intel.risk_map.blocked_from_release },
              ].map((cell) => (
                <div key={cell.label} className="bg-[#F4F4F2] border border-[#E5E5E5] rounded-xl p-3">
                  <div className="text-[10px] font-semibold uppercase tracking-[0.06em] text-[#666666]">{cell.label}</div>
                  <div className="font-serif-display text-[24px] leading-tight text-[#090909] mt-1">{cell.val}</div>
                </div>
              ))}
            </div>
            {intel.risk_map.safe_explanations && intel.risk_map.safe_explanations.length > 0 && (
              <div className="text-[12px] text-[#444444]">
                <span className="font-semibold text-[#090909]">Safe Explanations:</span>{" "}
                {intel.risk_map.safe_explanations.join(", ")}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Measured Privacy Assessments Table */}
      <div className="bg-white border border-[#DADADA] rounded-2xl overflow-hidden">
        <div className="px-6 py-4 border-b border-[#E5E5E5]">
          <h2 className="text-[15px] font-semibold text-[#090909]">
            Measured Privacy Assessments ({intel?.assessments.length ?? 0})
          </h2>
        </div>
        {!intel || intel.assessments.length === 0 ? (
          <div className="p-6">
            <EmptyState
              title="No privacy assessments measured"
              description="Upload and process a dataset to generate real PII detection and risk assessments."
            />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-[#E5E5E5] bg-[#F4F4F2]/60">
                  {["Assessment", "Job ID", "PII Detected", "Residual Leaks", "Canary", "QI Risk", "Eligible"].map((h) => (
                    <th key={h} className="px-5 py-3 text-[11px] font-semibold uppercase tracking-[0.05em] text-[#666666]">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-[#E5E5E5]">
                {intel.assessments.map((a) => (
                  <tr key={a.id} className="hover:bg-[#F4F4F2]/40">
                    <td className="px-5 py-3 text-[12px] font-mono text-[#090909]">{a.id}</td>
                    <td className="px-5 py-3 text-[12px] font-mono text-[#666666]">{a.job_id}</td>
                    <td className="px-5 py-3 text-[13px] font-semibold">{a.pii_detected}</td>
                    <td className="px-5 py-3 text-[13px]">{a.residual_leakage}</td>
                    <td className="px-5 py-3">
                      <StatusBadge status={a.canary_status} />{" "}
                      <span className="text-[11.5px] text-[#666666] ml-1">
                        ({a.canary_leaks}/{a.canary_planted})
                      </span>
                    </td>
                    <td className="px-5 py-3 text-[13px]">
                      {a.qi_risk_score}% ({a.reid_risk_level})
                    </td>
                    <td className="px-5 py-3">
                      <StatusBadge status={a.release_eligible ? "PASS" : "BLOCKED"} />
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
