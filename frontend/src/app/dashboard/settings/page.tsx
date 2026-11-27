"use client";

import { useEffect, useState } from "react";
import { api, type SettingsData } from "@/lib/api";
import { PageHeader } from "@/components/ui/PageHeader";
import { ErrorState, LoadingState } from "@/components/ui/StatePanels";
import { Save, CheckCircle2, Download } from "lucide-react";

interface DiagnosticsData {
  desktop_runtime: string;
  api_status: string;
  engine_status: string;
  database_status: string;
  encryption_configured: boolean;
  offline_mode: boolean;
  disk_free_bytes: number;
  disk_total_bytes: number;
  data_dir: string;
  version: string;
}

export default function SettingsPage() {
  const [settings, setSettings] = useState<SettingsData | null>(null);
  const [diag, setDiag] = useState<DiagnosticsData | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api.settings().then(setSettings).catch((e) => setError(e.message));
    api.diagnostics().then(setDiag).catch(() => {});
  }, []);

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    if (!settings) return;
    setSaving(true);
    setSaved(false);
    setError("");
    try {
      const updated = await api.updateSettings({
        output_format: settings.output_format,
        quarantine_threshold: settings.quarantine_threshold,
        multilingual_enabled: settings.multilingual_enabled,
      });
      setSettings(updated);
      setSaved(true);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    }
    setSaving(false);
  }

  return (
    <div className="space-y-6 max-w-3xl">
      <PageHeader
        eyebrow="12 · CONFIGURATION"
        title="Settings"
        subtitle="Workspace status and privacy engine policy thresholds."
      />

      {error && <ErrorState message={error} />}

      {saved && (
        <div className="px-4 py-3 rounded-xl bg-[#ECF3EC] border border-[#C6DBC7] text-[13px] text-[#1E4620] flex items-center gap-2">
          <CheckCircle2 size={15} />
          <span>Settings saved.</span>
        </div>
      )}

      {!settings ? (
        <LoadingState label="Loading configuration…" />
      ) : (
        <div className="space-y-6">
          <div className="bg-white border border-[#DADADA] rounded-2xl p-6">
            <h2 className="text-[15px] font-semibold text-[#090909] mb-4">
              Workspace & Engine Status
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-[13px] text-[#666666]">
              <div>
                <span className="text-[#090909] font-medium">Workspace:</span>{" "}
                {settings.workspace.full_name}
              </div>
              <div>
                <span className="text-[#090909] font-medium">Default Organisation:</span>{" "}
                {settings.workspace.active_org_id || "org-hosp-a"}
              </div>
              <div>
                <span className="text-[#090909] font-medium">RAKSHA_SECRET:</span>{" "}
                {settings.raksha_secret_set ? "Set in environment" : "Practice fallback"}
              </div>
              <div>
                <span className="text-[#090909] font-medium">Engine Mode:</span> CPU-only · Offline-first
              </div>
            </div>
          </div>

          {diag && (
            <div className="bg-white border border-[#DADADA] rounded-2xl p-6">
              <div className="flex items-center justify-between gap-3 mb-4">
                <h2 className="text-[15px] font-semibold text-[#090909]">
                  Offline System Diagnostics
                </h2>
                <a
                  href={api.briefPdfUrl()}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#090909] text-white text-[12px] font-medium hover:bg-[#222222]"
                >
                  <Download size={13} />
                  <span>Operational PDF</span>
                </a>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-[13px] text-[#666666]">
                <div><span className="text-[#090909] font-medium">Runtime:</span> {diag.desktop_runtime}</div>
                <div><span className="text-[#090909] font-medium">Local API:</span> {diag.api_status}</div>
                <div><span className="text-[#090909] font-medium">Privacy Engine:</span> {diag.engine_status}</div>
                <div><span className="text-[#090909] font-medium">Database:</span> {diag.database_status}</div>
                <div><span className="text-[#090909] font-medium">Encryption Key:</span> {diag.encryption_configured ? "Configured" : "Not Configured"}</div>
                <div><span className="text-[#090909] font-medium">Free Disk Space:</span> {(diag.disk_free_bytes / (1024 ** 3)).toFixed(2)} GB</div>
                <div className="sm:col-span-2 truncate"><span className="text-[#090909] font-medium">Storage Path:</span> {diag.data_dir}</div>
                <div><span className="text-[#090909] font-medium">Version:</span> {diag.version}</div>
              </div>
            </div>
          )}

          <form
            onSubmit={handleSave}
            className="bg-white border border-[#DADADA] rounded-2xl p-6 space-y-5"
          >
            <h2 className="text-[15px] font-semibold text-[#090909]">
              Privacy Engine Policy
            </h2>

            <div>
              <label className="block text-[12.5px] font-medium text-[#090909] mb-1.5">
                Output Format
              </label>
              <input
                value={settings.output_format}
                onChange={(e) => setSettings({ ...settings, output_format: e.target.value })}
                className="w-full px-3 py-2 rounded-lg bg-[#F4F4F2]/60 border border-[#DADADA] text-[13.5px] focus:outline-none focus:border-[#090909]"
              />
            </div>

            <div>
              <label className="block text-[12.5px] font-medium text-[#090909] mb-1.5">
                Quarantine Threshold
              </label>
              <input
                type="number"
                step="0.05"
                value={settings.quarantine_threshold}
                onChange={(e) =>
                  setSettings({ ...settings, quarantine_threshold: Number(e.target.value) })
                }
                className="w-full px-3 py-2 rounded-lg bg-[#F4F4F2]/60 border border-[#DADADA] text-[13.5px] focus:outline-none focus:border-[#090909]"
              />
            </div>

            <label className="flex items-center gap-2.5 text-[13.5px] text-[#090909] cursor-pointer">
              <input
                type="checkbox"
                checked={settings.multilingual_enabled}
                onChange={(e) =>
                  setSettings({ ...settings, multilingual_enabled: e.target.checked })
                }
              />
              <span>Enable Multilingual PII Detection</span>
            </label>

            <button
              type="submit"
              disabled={saving}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-[#090909] text-white text-[13px] font-medium hover:bg-[#222222] disabled:opacity-50"
            >
              <Save size={14} />
              <span>{saving ? "Saving…" : "Save Settings"}</span>
            </button>
          </form>
        </div>
      )}
    </div>
  );
}
