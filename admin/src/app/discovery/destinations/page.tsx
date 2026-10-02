"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";

import { FormError } from "@/components/FormError";
import { StatusBadge } from "@/components/StatusBadge";
import { ApiError } from "@/services/api";
import { discoveryService } from "@/services/discovery.service";
import type { AdminDestination, DiscoveryReference, LifecycleStatus } from "@/types/discovery";

export default function DestinationsPage() {
  const [items, setItems] = useState<AdminDestination[]>([]); const [reference, setReference] = useState<DiscoveryReference | null>(null); const [search, setSearch] = useState(""); const [lifecycle, setLifecycle] = useState<LifecycleStatus | "">(""); const [districtId, setDistrictId] = useState(0); const [applied, setApplied] = useState({query: "", lifecycle: "" as LifecycleStatus | "", districtId: 0}); const [loading, setLoading] = useState(true); const [error, setError] = useState("");
  async function load() { setLoading(true); setError(""); try { const [result, ref] = await Promise.all([discoveryService.destinations({query: applied.query || undefined, lifecycle: applied.lifecycle || undefined, district_id: applied.districtId || undefined}), reference ? Promise.resolve(reference) : discoveryService.reference()]); setItems(result.items); setReference(ref); } catch (caught) { setError(caught instanceof ApiError ? caught.message : "Unable to load destinations."); } finally { setLoading(false); } }
  // eslint-disable-next-line react-hooks/set-state-in-effect, react-hooks/exhaustive-deps
  useEffect(() => { void load(); }, [applied]);
  function filter(event: FormEvent) { event.preventDefault(); setApplied({query: search.trim(), lifecycle, districtId}); }
  return <div className="mx-auto max-w-7xl"><div className="mb-7 flex flex-wrap items-center justify-between gap-4"><div><p className="eyebrow">Discovery management</p><h1 className="page-title">Destinations</h1><p className="page-subtitle">Create and publish customer-facing locations inside the canonical 36-district taxonomy.</p></div><Link href="/discovery/destinations/new" className="btn-primary">New destination</Link></div>
    <form onSubmit={filter} className="panel grid gap-3 md:grid-cols-[1fr_220px_220px_auto]"><label className="text-sm font-bold">Search<input value={search} onChange={(event) => setSearch(event.target.value)} className="input mt-2" placeholder="Name or slug" /></label><label className="text-sm font-bold">District<select value={districtId} onChange={(event) => setDistrictId(Number(event.target.value))} className="input mt-2"><option value={0}>All districts</option>{reference?.districts.map((value) => <option value={value.id} key={value.id}>{value.name}</option>)}</select></label><label className="text-sm font-bold">Lifecycle<select value={lifecycle} onChange={(event) => setLifecycle(event.target.value as LifecycleStatus | "")} className="input mt-2"><option value="">All</option><option>DRAFT</option><option>PUBLISHED</option><option>UNPUBLISHED</option></select></label><button className="btn-primary self-end">Apply filters</button></form><div className="mt-4"><FormError message={error} /></div>
    {loading ? <div className="panel mt-5">Loading destinations…</div> : <div className="panel mt-5 overflow-x-auto p-0"><table className="min-w-full text-left text-sm"><thead className="border-b bg-slate-50 text-xs uppercase tracking-wide text-slate-500"><tr>{["Destination","District","Status","Source","Updated","Action"].map((value) => <th className="px-4 py-3" key={value}>{value}</th>)}</tr></thead><tbody className="divide-y">{items.map((item) => <tr key={item.id}><td className="px-4 py-4"><strong>{item.name}</strong><span className="block text-xs text-slate-500">{item.slug}</span></td><td className="px-4 py-4">{item.district_name}</td><td className="px-4 py-4"><StatusBadge status={item.status} /></td><td className="px-4 py-4">{item.content_source}{item.admin_overridden ? " · override" : ""}</td><td className="px-4 py-4 whitespace-nowrap">{new Date(item.updated_at).toLocaleDateString()}</td><td className="px-4 py-4"><Link href={`/discovery/destinations/${item.id}`} className="link">Edit / preview</Link></td></tr>)}</tbody></table>{!items.length && <p className="p-8 text-center text-slate-500">No destinations match these filters.</p>}</div>}
  </div>;
}
