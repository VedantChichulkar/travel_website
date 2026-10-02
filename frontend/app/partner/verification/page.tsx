"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { authService } from "@/src/services/auth.service";
import { partnerService } from "@/src/services/partner.service";
import { tokenStorage } from "@/src/services/token-storage";
import type { PartnerOverview, VerificationData } from "@/src/types/partner";

// ─── SVG Icons ─────────────────────────────────────────────────────────────────

function IconGrid() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="3" width="7" height="7" /><rect x="14" y="3" width="7" height="7" />
      <rect x="14" y="14" width="7" height="7" /><rect x="3" y="14" width="7" height="7" />
    </svg>
  );
}
function IconBuilding() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M6 22V4a2 2 0 012-2h8a2 2 0 012 2v18z" />
      <path d="M6 12H4a2 2 0 00-2 2v8h4" /><path d="M18 9h2a2 2 0 012 2v11h-4" />
      <path d="M10 6h4M10 10h4M10 14h4M10 18h4" />
    </svg>
  );
}
function IconShield() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
    </svg>
  );
}
function IconLogout() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4" /><polyline points="16 17 21 12 16 7" />
      <line x1="21" y1="12" x2="9" y2="12" />
    </svg>
  );
}
function IconMenu() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="3" y1="6" x2="21" y2="6" /><line x1="3" y1="12" x2="21" y2="12" /><line x1="3" y1="18" x2="21" y2="18" />
    </svg>
  );
}
function IconX() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  );
}

// ─── Status Badge ──────────────────────────────────────────────────────────────

const STATUS_CONFIGS: Record<string, { color: string; dot: string; pulse?: boolean; label?: string }> = {
  ACTIVE:   { color: "bg-emerald-100 text-emerald-800 border-emerald-200", dot: "bg-emerald-500" },
  DRAFT:    { color: "bg-slate-100 text-slate-700 border-slate-200", dot: "bg-slate-400" },
  PENDING:  { color: "bg-amber-100 text-amber-800 border-amber-200", dot: "bg-amber-500", pulse: true, label: "Under Review" },
  APPROVED: { color: "bg-emerald-100 text-emerald-800 border-emerald-200", dot: "bg-emerald-500", label: "Approved" },
  REJECTED: { color: "bg-red-100 text-red-800 border-red-200", dot: "bg-red-500", label: "Rejected" },
  ADDITIONAL_INFO_REQUIRED: { color: "bg-orange-100 text-orange-800 border-orange-200", dot: "bg-orange-500", pulse: true, label: "Action Required" },
  NEEDS_CHANGES: { color: "bg-orange-100 text-orange-800 border-orange-200", dot: "bg-orange-500", pulse: true, label: "Needs Changes" },
};

function StatusBadge({ status }: { status: string }) {
  const cfg = STATUS_CONFIGS[status] ?? { color: "bg-slate-100 text-slate-700 border-slate-200", dot: "bg-slate-400" };
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-bold ${cfg.color}`}>
      <span className={`h-2 w-2 rounded-full flex-shrink-0 ${cfg.dot}${cfg.pulse ? " animate-pulse" : ""}`} />
      {cfg.label ?? status}
    </span>
  );
}

function IconBed() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M2 4v16M2 8h18a2 2 0 0 1 2 2v10M2 17h20M6 8v9" />
    </svg>
  );
}

// ─── Shared Sidebar ────────────────────────────────────────────────────────────

function Sidebar({
  hotelName, initials, userName, onLogout, mobileOpen, onMobileClose,
}: {
  hotelName: string; initials: string; userName: string;
  onLogout: () => void; mobileOpen: boolean; onMobileClose: () => void;
}) {
  const navItems = [
    { href: "/partner/dashboard", label: "Dashboard", icon: <IconGrid />, id: "nav-dashboard" },
    { href: "/partner/hotel-profile", label: "Hotel Profile", icon: <IconBuilding />, id: "nav-hotel-profile" },
    { href: "/partner/room-types", label: "Room Types", icon: <IconBed />, id: "nav-room-types" },
    { href: "/partner/operations", label: "Hotel Operations", icon: <IconGrid />, id: "nav-operations" },
    { href: "/partner/settlements", label: "Settlements", icon: "₹", id: "nav-settlements" },
    { href: "/partner/reviews", label: "Guest Reviews", icon: "★", id: "nav-reviews" },
    { href: "/partner/verification", label: "Verification", icon: <IconShield />, id: "nav-verification" },
  ];
  const isActive = (href: string) =>
    typeof window !== "undefined" && window.location.pathname === href;

  const content = (
    <div className="flex flex-col h-full">
      <div className="px-5 py-5 border-b border-slate-100">
        <div className="flex items-center gap-3">
          <div className="grid h-8 w-8 flex-shrink-0 place-items-center rounded-lg bg-[#172554] text-white text-xs font-black">M</div>
          <div className="min-w-0">
            <p className="text-xs font-black tracking-tight text-[#172554]">Maharashtra Tourist Places Portal</p>
            <p className="text-xs text-slate-400 truncate">{hotelName}</p>
          </div>
        </div>
      </div>
      <nav className="flex-1 py-4 px-3 space-y-0.5">
        {navItems.map((item) => (
          <Link key={item.href} id={item.id} href={item.href} onClick={onMobileClose}
            className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-bold transition-all duration-150 ${
              isActive(item.href) ? "bg-[#172554] text-white shadow-sm" : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
            }`}>
            <span className={isActive(item.href) ? "text-white" : "text-slate-400"}>{item.icon}</span>
            {item.label}
          </Link>
        ))}
      </nav>
      <div className="px-3 pb-5 border-t border-slate-100 pt-4 space-y-1">
        <div className="flex items-center gap-3 px-3 py-2">
          <div className="grid h-8 w-8 flex-shrink-0 place-items-center rounded-full bg-[#ed6a3a] text-white text-xs font-black">{initials}</div>
          <span className="text-sm font-semibold text-slate-700 truncate">{userName}</span>
        </div>
        <button id="btn-sidebar-logout" onClick={onLogout}
          className="flex w-full items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-bold text-slate-500 hover:bg-red-50 hover:text-red-700 transition-colors">
          <span className="text-slate-400"><IconLogout /></span>Logout
        </button>
      </div>
    </div>
  );

  return (
    <>
      <aside className="hidden lg:flex flex-col w-64 flex-shrink-0 bg-white border-r border-slate-200 min-h-screen sticky top-0 max-h-screen overflow-y-auto">
        {content}
      </aside>
      {mobileOpen && (
        <>
          <div className="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm lg:hidden" onClick={onMobileClose} />
          <aside className="fixed inset-y-0 left-0 z-50 w-72 bg-white shadow-2xl flex flex-col lg:hidden">
            <button onClick={onMobileClose} className="absolute top-4 right-4 p-1 text-slate-400 hover:text-slate-700" aria-label="Close menu"><IconX /></button>
            {content}
          </aside>
        </>
      )}
    </>
  );
}

// ─── Info Row ──────────────────────────────────────────────────────────────────

function InfoRow({ label, value, children }: { label: string; value?: string | null; children?: React.ReactNode }) {
  return (
    <div>
      <dt className="text-xs font-black tracking-[0.1em] uppercase text-slate-400 mb-1">{label}</dt>
      <dd className="text-sm font-bold text-slate-800">{children ?? value ?? <span className="text-slate-400">—</span>}</dd>
    </div>
  );
}

// ─── Status Indicator Card ─────────────────────────────────────────────────────

function VerificationStatusCard({ ver }: { ver: VerificationData }) {
  const status = ver.verification_status;

  const bannerConfigs: Record<string, { bg: string; border: string; icon: string; title: string; body: string }> = {
    APPROVED: {
      bg: "bg-emerald-50", border: "border-emerald-200", icon: "✓",
      title: "Verification approved",
      body: "Your hotel has been verified by Maharashtra Tourist Places. Your portal is active and your property is visible on the platform.",
    },
    PENDING: {
      bg: "bg-amber-50", border: "border-amber-200", icon: "⏳",
      title: "Under review",
      body: "The Maharashtra Tourist Places team is reviewing your submission. Typical review time is 1–3 business days.",
    },
    REJECTED: {
      bg: "bg-red-50", border: "border-red-200", icon: "✗",
      title: "Verification rejected",
      body: "Your verification documents were not approved. Please address the rejection reason and re-submit via the Onboarding page.",
    },
    ADDITIONAL_INFO_REQUIRED: {
      bg: "bg-orange-50", border: "border-orange-200", icon: "!",
      title: "Additional information required",
      body: "Maharashtra Tourist Places admin has requested more information. Please review the admin notes and update your submission via Onboarding.",
    },
    NEEDS_CHANGES: {
      bg: "bg-orange-50", border: "border-orange-200", icon: "!",
      title: "Changes requested",
      body: "Maharashtra Tourist Places admin requested corrections. Your original verification fee remains valid; update and resubmit your application.",
    },
  };

  const cfg = bannerConfigs[status] ?? bannerConfigs["PENDING"];

  return (
    <div className={`rounded-2xl border ${cfg.bg} ${cfg.border} p-6 flex gap-5`} role="status">
      <div className="flex-shrink-0 h-12 w-12 rounded-full bg-white border border-slate-200 grid place-items-center text-xl font-black text-slate-700">
        {cfg.icon}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1 flex-wrap">
          <p className="font-black text-slate-800">{cfg.title}</p>
          <StatusBadge status={status} />
        </div>
        <p className="text-sm text-slate-600">{cfg.body}</p>

        {ver.rejection_reason && (
          <div className="mt-4 p-3 rounded-xl bg-white border border-red-200">
            <p className="text-xs font-black tracking-widest text-red-500 uppercase mb-1">Rejection Reason</p>
            <p className="text-sm text-red-800">{ver.rejection_reason}</p>
          </div>
        )}
        {ver.admin_notes && status !== "APPROVED" && (
          <div className="mt-4 p-3 rounded-xl bg-white border border-slate-200">
            <p className="text-xs font-black tracking-widest text-slate-400 uppercase mb-1">Notes from Maharashtra Tourist Places Team</p>
            <p className="text-sm text-slate-700">{ver.admin_notes}</p>
          </div>
        )}

        {(status === "ADDITIONAL_INFO_REQUIRED" || status === "NEEDS_CHANGES") && (
          <Link
            href="/partner/onboarding"
            id="link-resubmit-verification"
            className="inline-flex items-center gap-1.5 mt-4 px-4 py-2 rounded-xl bg-[#172554] text-white text-xs font-black hover:bg-[#0b163d] transition-colors"
          >
            Re-submit via Onboarding →
          </Link>
        )}
      </div>
    </div>
  );
}

// ─── Loading Skeleton ──────────────────────────────────────────────────────────

function LoadingSkeleton() {
  return (
    <div className="flex min-h-screen">
      <aside className="hidden lg:block w-64 flex-shrink-0 bg-white border-r border-slate-200">
        <div className="p-5 space-y-6"><div className="skeleton h-10 w-32 rounded-xl" /><div className="space-y-2">{[1,2,3].map(n=><div key={n} className="skeleton h-10 rounded-xl"/>)}</div></div>
      </aside>
      <div className="flex-1 p-6 space-y-5 max-w-5xl">
        <div className="skeleton h-12 w-64 rounded-xl" />
        <div className="skeleton h-36 rounded-2xl" />
        <div className="skeleton h-64 rounded-2xl" />
      </div>
    </div>
  );
}

// ─── Page ──────────────────────────────────────────────────────────────────────

export default function VerificationPage() {
  const router = useRouter();
  const [overview, setOverview] = useState<PartnerOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [userName, setUserName] = useState("");
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  const loadData = useCallback(async () => {
    setError("");
    try {
      const tokens = tokenStorage.getTokens();
      if (!tokens) { router.replace("/partner/login"); return; }
      const user = await authService.getCurrentUser();
      if (!user) { router.replace("/partner/login"); return; }
      if (user.role !== "HOTEL_PARTNER") { router.replace("/partner/login"); return; }
      setUserName(user.full_name);
      const data = await partnerService.getOverview();
      if (!data.has_hotel) { router.replace("/partner/onboarding"); return; }
      setOverview(data);
    } catch {
      setError("Could not load verification details. Please try again.");
    } finally {
      setLoading(false);
    }
  }, [router]);

  useEffect(() => { queueMicrotask(() => void loadData()); }, [loadData]);

  function handleLogout() {
    authService.logout();
    router.replace("/partner/login");
  }

  if (loading) return <LoadingSkeleton />;

  const initials = userName.split(/\s+/).slice(0, 2).map(n => n[0]).join("").toUpperCase();
  const hotel = overview?.hotel;
  const ver = overview?.verification;

  return (
    <div className="flex min-h-screen bg-[#f0f4f8]">
      <Sidebar
        hotelName={hotel?.name ?? "Your Hotel"}
        initials={initials}
        userName={userName}
        onLogout={handleLogout}
        mobileOpen={mobileNavOpen}
        onMobileClose={() => setMobileNavOpen(false)}
      />
      <div className="flex-1 flex flex-col min-w-0">
        {/* Mobile top bar */}
        <header className="lg:hidden bg-white border-b border-slate-200 sticky top-0 z-30 flex items-center justify-between px-4 h-14">
          <div className="flex items-center gap-2.5">
            <button id="btn-mobile-menu" onClick={() => setMobileNavOpen(true)} className="p-1 -ml-1 text-slate-500 hover:text-slate-800" aria-label="Open navigation"><IconMenu /></button>
            <span className="font-black text-[#172554] text-sm tracking-tight">Verification</span>
          </div>
          <div className="grid h-7 w-7 place-items-center rounded-full bg-[#ed6a3a] text-white text-xs font-black">{initials}</div>
        </header>

        <main className="flex-1 p-4 sm:p-6 lg:p-8 max-w-5xl w-full space-y-6">
          {/* Breadcrumb */}
          <div className="flex items-center gap-3">
            <Link href="/partner/dashboard" id="link-back-dashboard" className="text-xs font-black text-slate-400 hover:text-slate-700">← Dashboard</Link>
            <span className="text-slate-300">/</span>
            <span className="text-xs font-black text-slate-600">Verification</span>
          </div>

          {error && (
            <div className="bg-white rounded-2xl border border-red-200 shadow-sm p-10 text-center">
              <p className="text-lg font-black text-red-700 mb-2">Failed to load verification</p>
              <p className="text-slate-500 text-sm mb-6">{error}</p>
              <button id="btn-retry-verification" onClick={() => void loadData()} className="primary-button">Try again</button>
            </div>
          )}

          {!error && !ver && (
            <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-10 text-center">
              <p className="text-4xl mb-4">📋</p>
              <h2 className="text-lg font-black text-[#0b163d] mb-2">No verification submitted yet</h2>
              <p className="text-slate-500 text-sm mb-6">You haven&apos;t submitted verification documents yet. Complete your onboarding to get started.</p>
              <Link href="/partner/onboarding" id="link-go-onboarding" className="primary-button inline-flex">
                Go to Onboarding →
              </Link>
            </div>
          )}

          {!error && ver && (
            <>
              {/* Status card */}
              <VerificationStatusCard ver={ver} />

              {overview.verification_fee && (
                <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 sm:p-8">
                  <h2 className="text-base font-black text-[#0b163d] mb-4">Verification Fee</h2>
                  <dl className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
                    <InfoRow label="Fee" value={`${overview.verification_fee.currency} ${overview.verification_fee.amount}`} />
                    <InfoRow label="Payment Status" value={overview.verification_fee.payment_status.replaceAll("_", " ")} />
                    <InfoRow label="Payment Reference" value={overview.verification_fee.payment_reference ?? overview.verification_fee.provider_order_id} />
                    {overview.verification_fee.refund_status && <InfoRow label="Refund Status" value={overview.verification_fee.refund_status.replaceAll("_", " ")} />}
                    {overview.verification_fee.refund_reference && <InfoRow label="Refund Reference" value={overview.verification_fee.refund_reference} />}
                  </dl>
                  <p className="mt-4 text-xs text-slate-500">{overview.verification_fee.disclaimer}</p>
                  {overview.verification_fee.refund_failure_reason && <p className="mt-3 rounded-xl bg-amber-50 p-3 text-sm text-amber-800">{overview.verification_fee.refund_failure_reason}</p>}
                </div>
              )}

              {/* Business details */}
              <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 sm:p-8">
                <h2 className="text-base font-black text-[#0b163d] mb-5 tracking-tight">Business Details</h2>
                <dl className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
                  <InfoRow label="Business Name" value={ver.business_name} />
                  <InfoRow label="Business Type" value={ver.business_type?.replace(/_/g, " ")} />
                  {ver.gstin && <InfoRow label="GSTIN" value={ver.gstin} />}
                  {ver.pan && <InfoRow label="PAN" value={ver.pan} />}
                </dl>
              </div>

              {/* Bank details */}
              {(ver.bank_name || ver.bank_account_number || ver.bank_ifsc) && (
                <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 sm:p-8">
                  <h2 className="text-base font-black text-[#0b163d] mb-5 tracking-tight">Bank Account Details</h2>
                  <dl className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
                    {ver.bank_name && <InfoRow label="Bank Name" value={ver.bank_name} />}
                    {ver.bank_beneficiary_name && <InfoRow label="Account Holder" value={ver.bank_beneficiary_name} />}
                    {ver.bank_ifsc && <InfoRow label="IFSC Code" value={ver.bank_ifsc} />}
                    {ver.bank_account_number && (
                      <InfoRow label="Account Number">
                        <span className="font-mono text-sm text-slate-800">
                          ••••••{ver.bank_account_number.slice(-4)}
                        </span>
                      </InfoRow>
                    )}
                  </dl>
                </div>
              )}

              {/* Submission timeline */}
              <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 sm:p-8">
                <h2 className="text-base font-black text-[#0b163d] mb-5 tracking-tight">Review Timeline</h2>
                <dl className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
                  <InfoRow label="Verification ID" value={`#${ver.id}`} />
                  <InfoRow label="Current Status">
                    <StatusBadge status={ver.verification_status} />
                  </InfoRow>
                  {ver.document_proof_type && (
                    <InfoRow label="Document Type" value={ver.document_proof_type.replace(/_/g, " ")} />
                  )}
                  {ver.submitted_at && (
                    <InfoRow
                      label="Submitted On"
                      value={new Intl.DateTimeFormat("en-IN", { dateStyle: "long", timeStyle: "short" }).format(new Date(ver.submitted_at))}
                    />
                  )}
                  {ver.reviewed_at && (
                    <InfoRow
                      label="Reviewed On"
                      value={new Intl.DateTimeFormat("en-IN", { dateStyle: "long", timeStyle: "short" }).format(new Date(ver.reviewed_at))}
                    />
                  )}
                  <InfoRow
                    label="Record Created"
                    value={new Intl.DateTimeFormat("en-IN", { dateStyle: "medium" }).format(new Date(ver.created_at))}
                  />
                </dl>
              </div>
            </>
          )}
        </main>
      </div>
    </div>
  );
}
