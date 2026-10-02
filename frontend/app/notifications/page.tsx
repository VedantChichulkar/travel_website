"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { useAuth } from "@/src/context/AuthContext";
import { isCustomerRole } from "@/src/lib/portal-routing";
import { communicationService } from "@/src/services/communication.service";
import type { NotificationData } from "@/src/types/communication";

export default function NotificationsPage() {
  const router = useRouter(); const { loading: authLoading, user } = useAuth(); const [items, setItems] = useState<NotificationData[]>([]); const [unread, setUnread] = useState(0); const [loading, setLoading] = useState(true); const [error, setError] = useState("");
  const load = useCallback(async () => { setError(""); try { const result = await communicationService.listNotifications(); setItems(result.items); setUnread(result.unread_count); } catch (cause) { setError(cause instanceof Error ? cause.message : "Notifications could not be loaded."); } finally { setLoading(false); } }, []);
  useEffect(() => { if (user) queueMicrotask(() => void load()); }, [load, user]);
  useEffect(() => { if (user && isCustomerRole(user.role)) router.replace("/account/notifications"); }, [router, user]);
  async function read(item: NotificationData) { if (item.read_at) return; await communicationService.markNotificationRead(item.id); await load(); }
  async function readAll() { await communicationService.markAllNotificationsRead(); await load(); }
  if (authLoading) return <div className="container-shell py-16 text-sm text-slate-500">Verifying your account…</div>;
  if (user && isCustomerRole(user.role)) return <div className="container-shell py-16 text-sm text-slate-500">Opening customer notifications…</div>;
  return <main className="container-shell py-10 sm:py-14"><div className="flex flex-wrap items-end justify-between gap-4"><div><p className="eyebrow">Transactional updates</p><h1 className="page-title mt-3">Notifications</h1><p className="mt-3 text-slate-500">Booking, payment, stay, dispute, review, and settlement events. Marketing preferences are separate.</p></div>{unread > 0 && <button className="secondary-button" onClick={() => void readAll()}>Mark all read ({unread})</button>}</div>{error && <p role="alert" className="mt-6 rounded-xl bg-red-50 p-4 text-sm font-semibold text-red-700">{error}</p>}{!user ? <p className="mt-8 rounded-2xl border bg-white p-10 text-center text-slate-500">Sign in to see notifications.</p> : loading ? <div className="mt-8 space-y-3">{[1,2,3].map((key) => <div key={key} className="skeleton h-28 rounded-2xl" />)}</div> : items.length === 0 ? <p className="mt-8 rounded-2xl border bg-white p-10 text-center text-slate-500">No transactional notifications yet.</p> : <div className="mt-8 space-y-3">{items.map((item) => <button key={item.id} onClick={() => void read(item)} className={`w-full rounded-2xl border p-5 text-left shadow-sm transition hover:border-slate-300 ${item.read_at ? "bg-white" : "border-orange-200 bg-orange-50/50"}`}><span className="flex flex-wrap items-start justify-between gap-3"><span><strong className="text-[#0b163d]">{item.title}</strong><span className="mt-1 block text-sm leading-6 text-slate-600">{item.body}</span></span><time className="text-xs text-slate-400">{new Date(item.created_at).toLocaleString()}</time></span><span className="mt-3 flex flex-wrap gap-2">{item.jobs.map((job) => <span key={job.id} title={job.last_error ?? undefined} className="status-pill bg-slate-100 text-slate-500">{job.channel}: {job.status.replaceAll("_", " ")}</span>)}</span></button>)}</div>}</main>;
}
