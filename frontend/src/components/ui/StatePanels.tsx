import React from "react";
import { AlertTriangle, Inbox } from "lucide-react";

export function LoadingState({ label = "Loading telemetry…" }: { label?: string }) {
  return (
    <div className="bg-white border border-[#DADADA] rounded-2xl p-10 text-center">
      <div className="w-6 h-6 border-2 border-[#DADADA] border-t-[#090909] rounded-full animate-spin mx-auto mb-3" />
      <p className="text-[13.5px] text-[#666666]">{label}</p>
    </div>
  );
}

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="bg-white border border-[#DADADA] rounded-2xl p-10 text-center flex flex-col items-center justify-center">
      <div className="w-10 h-10 rounded-full bg-[#F4F4F2] border border-[#E5E5E5] flex items-center justify-center mb-3">
        <Inbox size={18} className="text-[#666666]" />
      </div>
      <h3 className="text-[14.5px] font-semibold text-[#090909]">{title}</h3>
      <p className="text-[13px] text-[#666666] mt-1 max-w-md">{description}</p>
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function ErrorState({ message }: { message: string }) {
  return (
    <div className="px-4 py-3 rounded-xl bg-[#FDF2F2] border border-[#E8C5C5] text-[13px] text-[#7F1D1D] flex items-center gap-2.5">
      <AlertTriangle size={16} className="shrink-0" />
      <span>{message}</span>
    </div>
  );
}

export function ConfirmationDialog({
  open,
  title,
  description,
  confirmLabel = "Confirm",
  onConfirm,
  onCancel,
}: {
  open: boolean;
  title: string;
  description: string;
  confirmLabel?: string;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="bg-white border border-[#DADADA] rounded-2xl max-w-md w-full p-6">
        <h3 className="font-serif-display text-[22px] text-[#090909] mb-2">{title}</h3>
        <p className="text-[13.5px] text-[#666666] leading-relaxed mb-6">{description}</p>
        <div className="flex justify-end gap-2.5">
          <button
            type="button"
            onClick={onCancel}
            className="px-4 py-2 rounded-lg bg-white border border-[#DADADA] text-[13px] font-medium text-[#090909] hover:bg-[#F4F4F2]"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={onConfirm}
            className="px-4 py-2 rounded-lg bg-[#090909] text-white text-[13px] font-medium hover:bg-[#222222]"
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
