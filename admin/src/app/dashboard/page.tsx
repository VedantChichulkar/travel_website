"use client";

import { AdminGuard } from "@/components/AdminGuard";
import { AdminNavigation } from "@/components/AdminNavigation";
import { useAdminAuth } from "@/context/AdminAuthContext";

export default function DashboardPage() {
  return (
    <AdminGuard>
      <DashboardContent />
    </AdminGuard>
  );
}

function DashboardContent() {
  const { admin } = useAdminAuth();
  if (!admin) return null;

  return (
    <div className="min-h-screen">
      <AdminNavigation />
      <main className="mx-auto max-w-6xl px-4 py-10 sm:px-6">
        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
          <div className="flex flex-wrap items-start justify-between gap-4 border-b border-slate-200 pb-6">
            <div>
              <p className="text-sm font-semibold uppercase tracking-[0.16em] text-indigo-700">Administration</p>
              <h1 className="mt-2 text-3xl font-bold tracking-tight">Admin Dashboard</h1>
            </div>
            <span className="rounded-full bg-emerald-50 px-3 py-1 text-sm font-semibold text-emerald-700">Backend connected</span>
          </div>
          <dl className="mt-6 grid gap-6 sm:grid-cols-3">
            <Detail label="Administrator" value={admin.full_name} />
            <Detail label="Email" value={admin.email} />
            <Detail label="Role" value={admin.role} />
          </dl>
          <p className="mt-8 rounded-lg bg-slate-50 p-4 text-sm text-slate-600">Administrator authentication is active. Business management modules have not been enabled yet.</p>
        </div>
      </main>
    </div>
  );
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-sm font-medium text-slate-500">{label}</dt>
      <dd className="mt-1 break-words font-semibold text-slate-950">{value}</dd>
    </div>
  );
}
