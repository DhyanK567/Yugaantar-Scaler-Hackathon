"use client";

import { useEffect, useState } from "react";
import { api, type Organisation } from "@/lib/api";
import { PageHeader } from "@/components/ui/PageHeader";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/StatePanels";
import { StatusBadge } from "@/components/dashboard/StatusBadge";
import { RefreshCw } from "lucide-react";

export default function OrganisationsPage() {
  const [orgs, setOrgs] = useState<Organisation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  function load() {
    setLoading(true);
    setError("");
    api
      .organisations()
      .then(setOrgs)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    load();
  }, []);

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="06 · INSTITUTIONAL DIRECTORY"
        title="Organisations"
        subtitle="Authorised hospitals, diagnostic laboratories, and research institutions for your account."
        actions={
          <button
            type="button"
            onClick={load}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-white border border-[#DADADA] text-[13px] font-medium text-[#090909] hover:bg-[#F4F4F2]"
          >
            <RefreshCw size={13} />
            <span>Refresh</span>
          </button>
        }
      />

      {error && <ErrorState message={error} />}

      {loading ? (
        <LoadingState label="Loading organisations…" />
      ) : orgs.length === 0 ? (
        <EmptyState
          title="No authorised organisations"
          description="Your account does not currently have active organisation memberships."
        />
      ) : (
        <div className="bg-white border border-[#DADADA] rounded-2xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-[#E5E5E5] bg-[#F4F4F2]/60">
                  {["Organisation", "Type", "Region", "Status", "Records Contributed", "Joined"].map((h) => (
                    <th key={h} className="px-5 py-3 text-[11px] font-semibold uppercase tracking-[0.05em] text-[#666666]">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-[#E5E5E5]">
                {orgs.map((org) => (
                  <tr key={org.id} className="hover:bg-[#F4F4F2]/40">
                    <td className="px-5 py-3.5 text-[13.5px] font-semibold text-[#090909]">{org.name}</td>
                    <td className="px-5 py-3.5 text-[13px] text-[#666666]">{org.org_type}</td>
                    <td className="px-5 py-3.5 text-[13px] text-[#666666]">{org.region}</td>
                    <td className="px-5 py-3.5">
                      <StatusBadge status={org.status.toLowerCase() === "active" ? "PASS" : org.status} />
                    </td>
                    <td className="px-5 py-3.5 text-[13px] font-medium text-[#090909]">
                      {org.records_contributed.toLocaleString()}
                    </td>
                    <td className="px-5 py-3.5 text-[12px] text-[#666666] whitespace-nowrap">
                      {new Date(org.joined_at * 1000).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
