"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { SafariRequestCard } from "@/src/components/safari/SafariAccount";
import { useAuth } from "@/src/context/AuthContext";
import { isCustomerRole } from "@/src/lib/portal-routing";
import { safariStatusDisplay } from "@/src/lib/safari-status";
import { safariService } from "@/src/services/safari.service";
import type { SafariRequest } from "@/src/types/safari";

export function SafariRequestDetail({ requestReference }: { requestReference: string }) {
  const { loading: authLoading, user } = useAuth();
  const [item, setItem] = useState<SafariRequest>(); const [loading, setLoading] = useState(true); const [error, setError] = useState(""); const [notice, setNotice] = useState("");
  const customer = user && isCustomerRole(user.role);
  const load = useCallback(async (silent = false) => { if (!silent) setLoading(true); setError(""); try { const owned = (await safariService.mine()).find((request) => request.request_reference === requestReference); if (!owned) throw new Error("Safari request not found"); setItem(await safariService.getRequest(owned.id)); } catch (cause) { setError(cause instanceof Error ? cause.message : "This Safari request could not be loaded."); } finally { if (!silent) setLoading(false); } }, [requestReference]);
  useEffect(() => { if (!authLoading && customer) queueMicrotask(() => { void load(); }); }, [authLoading, customer, load]);
  useEffect(() => { if (!customer || !item || safariStatusDisplay(item.status).terminal) return; const timer = window.setInterval(() => { void load(true); }, 30_000); return () => window.clearInterval(timer); }, [customer, item, load]);

  return <div><div className="mb-7"><Link href="/account/safaris" className="text-sm font-black text-[var(--accent)] hover:text-[var(--accent-strong)]">← All Safari requests</Link><p className="eyebrow mt-7">Safari booking</p><h1 className="page-title mt-2">Request details</h1><p className="mt-3 max-w-2xl text-sm leading-6 text-slate-600">This page is the source of truth for your current status, next action, payment, official booking, and secure documents.</p></div>
    {notice && <div role="status" className="mb-5 flex items-start justify-between gap-4 rounded-xl border border-blue-100 bg-blue-50 p-4 text-sm font-semibold text-blue-800"><span>{notice}</span><button type="button" onClick={() => setNotice("")} aria-label="Dismiss message">×</button></div>}
    {authLoading || (customer && loading) ? <div className="h-72 animate-pulse rounded-2xl border border-[var(--line)] bg-white p-7"><div className="h-6 w-52 rounded bg-slate-100" /><div className="mt-5 h-24 rounded bg-slate-100" /></div> : !customer ? <div className="content-card text-center"><h2 className="text-xl font-black text-[var(--brand)]">Customer sign-in required</h2><p className="mt-2 text-sm text-slate-600">Sign in to access this customer-owned Safari request and its secure documents.</p><Link href="/login" className="primary-button mt-5">Sign in</Link></div> : error ? <div role="alert" className="content-card border-red-200 text-center"><h2 className="text-xl font-black text-red-800">Request unavailable</h2><p className="mt-2 text-sm text-red-700">{error}</p><div className="mt-5 flex justify-center gap-3"><button type="button" onClick={() => void load()} className="primary-button">Try again</button><Link href="/account/safaris" className="secondary-button">Back to requests</Link></div></div> : item ? <SafariRequestCard item={item} onUpdate={(updated, message) => { setItem(updated); if (message) setNotice(message); }} onNotice={setNotice} /> : null}
  </div>;
}
