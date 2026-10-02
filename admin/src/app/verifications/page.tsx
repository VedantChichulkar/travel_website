"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { AdminShell } from "@/components/AdminShell";
import { useAdminAuth } from "@/context/AdminAuthContext";
import { verificationService, VerificationListItem, VerificationStatus } from "@/services/verification.service";

const STATUS_CONFIG: Record<VerificationStatus, { label: string; color: string; dot: string }> = {
  PENDING: { label: "Pending Review", color: "bg-amber-100 text-amber-800 border-amber-300", dot: "bg-amber-500" },
  APPROVED: { label: "Approved", color: "bg-emerald-100 text-emerald-800 border-emerald-300", dot: "bg-emerald-500" },
  REJECTED: { label: "Rejected", color: "bg-red-100 text-red-800 border-red-300", dot: "bg-red-500" },
  ADDITIONAL_INFO_REQUIRED: { label: "Info Required", color: "bg-orange-100 text-orange-800 border-orange-300", dot: "bg-orange-500" },
  NEEDS_CHANGES: { label: "Needs Changes", color: "bg-orange-100 text-orange-800 border-orange-300", dot: "bg-orange-500" },
};

function StatusBadge({ status }: { status: string }) {
  const cfg = STATUS_CONFIG[status as VerificationStatus] ?? { label: status.replaceAll("_", " "), color: "bg-slate-100 text-slate-700 border-slate-200", dot: "bg-slate-400" };
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-bold ${cfg.color}`}>
      <span className={`h-1.5 w-1.5 rounded-full ${cfg.dot}`} />
      {cfg.label}
    </span>
  );
}

const FILTER_OPTIONS: { label: string; value: VerificationStatus | "ALL" }[] = [
  { label: "All", value: "ALL" },
  { label: "Pending", value: "PENDING" },
  { label: "Approved", value: "APPROVED" },
  { label: "Rejected", value: "REJECTED" },
  { label: "Info Required", value: "ADDITIONAL_INFO_REQUIRED" },
  { label: "Needs Changes", value: "NEEDS_CHANGES" },
];

export default function VerificationsPage() {
  return (
    <AdminShell>
      <VerificationsContent />
    </AdminShell>
  );
}

function VerificationsContent() {
  const { admin } = useAdminAuth();
  const [items, setItems] = useState<VerificationListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [filter, setFilter] = useState<VerificationStatus | "ALL">("PENDING");

  useEffect(() => {
    if (!admin) return;
    queueMicrotask(() => {
      setLoading(true);
      setError("");
      verificationService
        .list(filter === "ALL" ? undefined : filter)
        .then(setItems)
        .catch(() => setError("Failed to load verification requests."))
        .finally(() => setLoading(false));
    });
  }, [admin, filter]);

  return (
    <div className="mx-auto max-w-6xl">
      {/* Header */}
      <div className="mb-8 flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.16em] text-indigo-700 mb-1">Administration</p>
          <h1 className="text-2xl font-bold tracking-tight">Hotel Verification Requests</h1>
          <p className="text-sm text-slate-500 mt-1">Review and approve hotel partner onboarding submissions.</p>
        </div>
        <div className="flex items-center gap-2 rounded-xl border border-slate-200 bg-white p-1 shadow-sm">
          {FILTER_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              onClick={() => setFilter(opt.value)}
              className={`rounded-lg px-3 py-1.5 text-sm font-semibold transition-colors ${filter === opt.value ? "bg-indigo-600 text-white" : "text-slate-600 hover:bg-slate-100"}`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      <div className="rounded-2xl border border-slate-200 bg-white shadow-sm overflow-hidden">
        {loading ? (
          <div className="p-12 text-center text-slate-400 text-sm">Loading…</div>
        ) : error ? (
          <div className="p-12 text-center text-red-600 text-sm font-semibold">{error}</div>
        ) : items.length === 0 ? (
          <div className="p-12 text-center">
            <p className="text-slate-400 text-sm">No verification requests found for this filter.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 border-b border-slate-200">
                <tr>
                  {["Hotel", "Location", "Partner", "Business", "Payment", "Status", "Submitted", "Action"].map((h) => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-black uppercase tracking-wider text-slate-500">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {items.map((item) => (
                  <tr key={item.id} className="hover:bg-slate-50 transition-colors">
                    <td className="px-4 py-4">
                      <p className="font-bold text-slate-900">{item.hotel_name}</p>
                      <p className="text-xs text-slate-400 mt-0.5">{item.hotel_slug}</p>
                    </td>
                    <td className="px-4 py-4">
                      <p className="text-slate-700">{item.hotel_city}</p>
                      <p className="text-xs text-slate-400">{item.hotel_state}</p>
                    </td>
                    <td className="px-4 py-4">
                      <p className="text-slate-700 font-medium">{item.partner_name ?? "—"}</p>
                      <p className="text-xs text-slate-400">{item.partner_email ?? "—"}</p>
                    </td>
                    <td className="px-4 py-4">
                      <p className="text-slate-700">{item.business_name}</p>
                      <p className="text-xs text-slate-400">{item.business_type.replace(/_/g, " ")}</p>
                    </td>
                    <td className="px-4 py-4">
                      <StatusBadge status={item.payment_status} />
                    </td>
                    <td className="px-4 py-4">
                      <StatusBadge status={item.verification_status} />
                    </td>
                    <td className="px-4 py-4 text-slate-500 text-xs">
                      {item.submitted_at
                        ? new Intl.DateTimeFormat("en-IN", { dateStyle: "medium" }).format(new Date(item.submitted_at))
                        : "—"}
                    </td>
                    <td className="px-4 py-4">
                      <Link href={`/verifications/${item.id}`}
                        className="inline-flex items-center gap-1 rounded-lg bg-indigo-50 px-3 py-1.5 text-xs font-bold text-indigo-700 hover:bg-indigo-100 transition-colors">
                        Review →
                      </Link>
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
