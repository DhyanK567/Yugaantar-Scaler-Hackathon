"use client";

import { useEffect, useState } from "react";
import { api, type JobRecord, type ThreatLabData } from "@/lib/api";
import { PageHeader } from "@/components/ui/PageHeader";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/StatePanels";
import { StatusBadge } from "@/components/dashboard/StatusBadge";
import { Play, RefreshCw } from "lucide-react";

export default function AttackSimulatorPage() {
  const [data, setData] = useState<ThreatLabData | null>(null);
  const [jobs, setJobs] = useState<JobRecord[]>([]);
  const [selectedJob, setSelectedJob] = useState("");
  const [running, setRunning] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  function load() {
    setLoading(true);
    setError("");
    Promise.all([api.threatLab(), api.jobs()])
      .then(([t, j]) => {
        setData(t);
        setJobs(j);
        if (j.length > 0 && !selectedJob) setSelectedJob(j[0].id);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    load();
  }, []);

  async function handleRunAttack() {
    if (!selectedJob) return;
    setRunning(true);
    setError("");
    try {
      await api.runAttackSimulator(selectedJob, "standard-7-vector");
      load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    }
    setRunning(false);
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="05 · ADVERSARIAL TESTING"
        title="Attack Simulator"
        subtitle="Executes deterministic 7-vector re-identification attacks against sanitised job outputs."
        actions={
          <>
            {jobs.length > 0 && (
              <select
                value={selectedJob}
                onChange={(e) => setSelectedJob(e.target.value)}
                aria-label="Select job"
                className="px-3 py-2 rounded-lg bg-white border border-[#DADADA] text-[13px] text-[#090909]"
              >
                {jobs.map((j) => (
                  <option key={j.id} value={j.id}>
                    {j.id} ({j.status})
                  </option>
                ))}
              </select>
            )}
            <button
              type="button"
              onClick={handleRunAttack}
              disabled={running || !selectedJob}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-[#090909] text-white text-[13px] font-medium hover:bg-[#222222] disabled:opacity-50"
            >
              <Play size={13} />
              <span>{running ? "Running…" : "Run simulation"}</span>
            </button>
            <button
              type="button"
              onClick={load}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-white border border-[#DADADA] text-[13px] font-medium text-[#090909] hover:bg-[#F4F4F2]"
            >
              <RefreshCw size={13} />
              <span>Refresh</span>
            </button>
          </>
        }
      />

      {error && <ErrorState message={error} />}

      <div className="bg-white border border-[#DADADA] rounded-2xl p-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-[0.08em] text-[#888888] mb-1">
            Residual Uniquely Distinguishable Rate
          </div>
          <div className="font-serif-display text-[38px] leading-none text-[#090909]">
            {data?.status === "MEASURED" && data.risk_score !== null ? `${data.risk_score}%` : "Not run"}
          </div>
        </div>
        <div className="text-[13px] text-[#666666]">
          {data?.attack_simulations && data.attack_simulations.length > 0
            ? `${data.attack_simulations.filter((a) => !a.success).length} / ${data.attack_simulations.length} vectors blocked`
            : "No attack simulations executed yet"}
        </div>
      </div>

      {loading ? (
        <LoadingState label="Loading threat lab telemetry…" />
      ) : !data?.attack_simulations || data.attack_simulations.length === 0 ? (
        <EmptyState
          title="No attack vectors evaluated"
          description="Process a dataset or select a job above and click Run simulation."
        />
      ) : (
        <div className="bg-white border border-[#DADADA] rounded-2xl overflow-hidden">
          <div className="px-6 py-4 border-b border-[#E5E5E5]">
            <h2 className="text-[15px] font-semibold text-[#090909]">Attack Vectors</h2>
          </div>
          <div className="divide-y divide-[#E5E5E5]">
            {data.attack_simulations.map((atk, idx) => (
              <div
                key={idx}
                className="px-6 py-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3"
              >
                <div>
                  <div className="text-[14px] font-semibold text-[#090909]">{atk.attack_type}</div>
                  <div className="text-[12.5px] text-[#666666] mt-0.5">
                    Mitigation: {atk.mitigation}
                  </div>
                </div>
                <div className="flex items-center gap-3 shrink-0">
                  <span className="text-[12px] text-[#666666]">
                    {atk.records_at_risk} records at risk
                  </span>
                  <StatusBadge status={atk.success ? "FAILED" : "PASS"} />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
