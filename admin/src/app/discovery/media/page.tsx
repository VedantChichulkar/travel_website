"use client";
/* eslint-disable @next/next/no-img-element -- public-media URLs are runtime values and already server-optimized */

import Link from "next/link";
import { useEffect, useState } from "react";
import { FormError } from "@/components/FormError";
import { StatusBadge } from "@/components/StatusBadge";
import { ApiError } from "@/services/api";
import { discoveryService } from "@/services/discovery.service";
import type { PublicMediaAsset } from "@/types/discovery";

export default function PublicMediaPage() {
  const [items, setItems] = useState<PublicMediaAsset[]>([]); const [status, setStatus] = useState<"ACTIVE" | "RETIRED" | "">(""); const [error, setError] = useState(""); const [loading, setLoading] = useState(true);
  async function load() { setLoading(true); setError(""); try { setItems(await discoveryService.media(status || undefined)); } catch (caught) { setError(caught instanceof ApiError ? caught.message : "Unable to load public media."); } finally { setLoading(false); } }
  // eslint-disable-next-line react-hooks/set-state-in-effect, react-hooks/exhaustive-deps
  useEffect(() => { void load(); }, [status]);
  return <div className="mx-auto max-w-7xl"><div className="mb-7"><p className="eyebrow">Discovery management</p><h1 className="page-title">Public media</h1><p className="page-subtitle">Rights provenance, optimization output, and replacement history for customer-facing imagery.</p></div>
    <div className="panel flex flex-wrap items-end justify-between gap-4"><label className="text-sm font-bold">Asset status<select value={status} onChange={(event) => setStatus(event.target.value as typeof status)} className="input mt-2 w-56"><option value="">All</option><option>ACTIVE</option><option>RETIRED</option></select></label><p className="max-w-xl text-sm text-slate-500">Upload media from a destination or place editor so subject identity and rights records stay attached to the correct entity.</p></div><div className="mt-4"><FormError message={error} /></div>
    {loading ? <div className="panel mt-5">Loading media…</div> : <div className="mt-5 grid gap-5 lg:grid-cols-2">{items.map((item) => <article className="panel grid gap-4 sm:grid-cols-[180px_1fr]" key={item.id}><img src={item.public_url} alt={item.alt_text} className="h-32 w-full rounded-lg object-cover" /><div><div className="flex flex-wrap items-center gap-2"><StatusBadge status={item.status} /><span className="text-xs font-bold text-blue-800">{item.specificity}</span></div><h2 className="mt-2 font-black">{item.entity_type} #{item.entity_id}</h2><p className="mt-1 text-sm text-slate-600">{item.alt_text}</p><dl className="mt-3 grid grid-cols-2 gap-2 text-xs"><div><dt className="text-slate-500">Creator / owner</dt><dd>{item.creator_owner}</dd></div><div><dt className="text-slate-500">Usage basis</dt><dd>{item.usage_basis}</dd></div><div><dt className="text-slate-500">Output</dt><dd>{item.width}×{item.height} · {Math.ceil(item.size_bytes / 1024)} KB</dd></div><div><dt className="text-slate-500">Verified</dt><dd>{item.rights_verified_at}</dd></div></dl><Link href={`/discovery/${item.entity_type === "PLACE" ? "places" : "destinations"}/${item.entity_id}`} className="link mt-3 inline-block">Open entity</Link></div></article>)}</div>}
    {!loading && !items.length && <div className="panel mt-5 text-center text-slate-500">No public media assets match this filter.</div>}
  </div>;
}
