"use client";
import { useEffect, useState } from "react";
import { api, type Settings } from "@/lib/api";
import { Save, AlertTriangle, CheckCircle2 } from "lucide-react";

export default function SettingsPage() {
  const [settings, setSettings] = useState<Settings | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .settings()
      .then(setSettings)
      .catch((e) => setError(e.message));
  }, []);

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    if (!settings) return;
    setSaving(true);
    setSaved(false);
    setError("");
    try {
      const updated = await api.updateSettings(settings);
      setSettings(updated);
      setSaved(true);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    }
    setSaving(false);
  }

  return (
    <div style={{ padding: "32px 36px", maxWidth: 720 }}>
      <div style={{ marginBottom: 28 }}>
        <h1 style={{ fontSize: 24, fontWeight: 700, color: "#050505", letterSpacing: "-0.8px", marginBottom: 4 }}>
          Settings
        </h1>
        <p style={{ fontSize: 13.5, color: "#777777" }}>
          Configure privacy engine thresholds and output policy.
        </p>
      </div>

      {error && (
        <div
          style={{
            padding: "12px 16px",
            background: "#FFFBF0",
            border: "1.5px solid #E6D5A0",
            borderRadius: 8,
            fontSize: 13,
            color: "#7A5C00",
            marginBottom: 20,
            display: "flex",
            alignItems: "center",
            gap: 8,
          }}
        >
          <AlertTriangle size={15} />
          {error}
        </div>
      )}

      {saved && (
        <div
          style={{
            padding: "12px 16px",
            background: "#F2F8F2",
            border: "1.5px solid #B6DAB6",
            borderRadius: 8,
            fontSize: 13,
            color: "#2D7A2D",
            marginBottom: 20,
            display: "flex",
            alignItems: "center",
            gap: 8,
          }}
        >
          <CheckCircle2 size={15} />
          Settings saved.
        </div>
      )}

      {settings && (
        <form
          onSubmit={handleSave}
          style={{
            background: "#FFFFFF",
            border: "1.5px solid #DCDCDC",
            borderRadius: 10,
            padding: 24,
            display: "flex",
            flexDirection: "column",
            gap: 20,
          }}
        >
          <div>
            <label style={{ display: "block", fontSize: 12.5, fontWeight: 600, color: "#050505", marginBottom: 6 }}>
              Output Format
            </label>
            <input
              value={settings.output_format}
              onChange={(e) => setSettings({ ...settings, output_format: e.target.value })}
              style={{
                width: "100%",
                padding: "9px 12px",
                border: "1.5px solid #DCDCDC",
                borderRadius: 7,
                fontSize: 14,
                background: "#FAFAFA",
              }}
            />
          </div>

          <div>
            <label style={{ display: "block", fontSize: 12.5, fontWeight: 600, color: "#050505", marginBottom: 6 }}>
              Quarantine Threshold
            </label>
            <input
              type="number"
              step="0.05"
              value={settings.quarantine_threshold}
              onChange={(e) =>
                setSettings({ ...settings, quarantine_threshold: Number(e.target.value) })
              }
              style={{
                width: "100%",
                padding: "9px 12px",
                border: "1.5px solid #DCDCDC",
                borderRadius: 7,
                fontSize: 14,
                background: "#FAFAFA",
              }}
            />
          </div>

          <label style={{ display: "flex", alignItems: "center", gap: 10, fontSize: 13.5, color: "#050505", cursor: "pointer" }}>
            <input
              type="checkbox"
              checked={settings.multilingual_enabled}
              onChange={(e) => setSettings({ ...settings, multilingual_enabled: e.target.checked })}
            />
            Enable Multilingual PII Detection
          </label>

          <button
            type="submit"
            disabled={saving}
            style={{
              alignSelf: "flex-start",
              display: "inline-flex",
              alignItems: "center",
              gap: 6,
              padding: "10px 20px",
              background: "#050505",
              color: "#FFFFFF",
              border: "none",
              borderRadius: 7,
              fontSize: 13.5,
              fontWeight: 600,
              cursor: saving ? "not-allowed" : "pointer",
            }}
          >
            <Save size={14} />
            {saving ? "Saving…" : "Save Settings"}
          </button>
        </form>
      )}
    </div>
  );
}
