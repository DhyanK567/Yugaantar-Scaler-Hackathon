import {
  FileText,
  Users,
  Shield,
  HeartPulse,
  TrendingUp,
  CheckCircle2,
} from "lucide-react";
import type { DashboardOverview } from "@/lib/api";
import { MetricCard } from "./MetricCard";

interface MetricGridProps {
  metrics: DashboardOverview["metrics"];
}

export function MetricGrid({ metrics }: MetricGridProps) {
  return (
    <section aria-label="Privacy Performance Metrics">
      <div className="flex items-center justify-between mb-3.5">
        <h2 className="text-[15px] font-semibold text-[#050505]">
          Privacy Performance Metrics
        </h2>
        <span className="text-[12px] text-[#666666]">
          Click any card to inspect evidence
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        <MetricCard
          label="Files Processed"
          metric={metrics.files_processed}
          href="/dashboard/datasets"
          icon={FileText}
        />
        <MetricCard
          label="Records Processed"
          metric={metrics.records_processed}
          href="/dashboard/datasets"
          icon={Users}
        />
        <MetricCard
          label="PII Detected"
          metric={metrics.pii_detected}
          href="/dashboard/privacy-intelligence"
          icon={Shield}
        />
        <MetricCard
          label="Clinical Values Preserved"
          metric={metrics.clinical_preserved}
          href="/dashboard/clinical-integrity"
          icon={HeartPulse}
        />
        <MetricCard
          label="Identity Precision"
          metric={metrics.identity_precision}
          href="/dashboard/identity-continuity"
          icon={TrendingUp}
        />
        <MetricCard
          label="Canary Leaks"
          metric={metrics.canary_leaks}
          href="/dashboard/attack-simulator"
          icon={CheckCircle2}
        />
      </div>
    </section>
  );
}
