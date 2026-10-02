"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useCallback, useEffect, useState } from "react";

import { FormError } from "@/components/FormError";
import { StatusBadge } from "@/components/StatusBadge";
import { ApiError } from "@/services/api";
import { hotelService } from "@/services/hotel.service";
import { HOTEL_STATUSES, type Hotel, type HotelStatus } from "@/types/hotel";
import { controlService } from "@/services/control.service";

export default function HotelsPage() {
  const router = useRouter();
  const [hotels, setHotels] = useState<Hotel[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState<HotelStatus | "">("");
  const [appliedSearch, setAppliedSearch] = useState("");
  const [appliedStatus, setAppliedStatus] = useState<HotelStatus | "">("");

  const load = useCallback(async () => {
    await Promise.resolve();
    setLoading(true); setError("");
    try { const query=new URLSearchParams();if(appliedSearch)query.set("search",appliedSearch);if(appliedStatus)query.set("hotel_status",appliedStatus);query.set("limit","200");setHotels(await hotelService.list(`?${query}`)); }
    catch (caught) {
      if (caught instanceof ApiError && caught.status === 401) return router.replace("/login");
      setError(caught instanceof ApiError ? caught.message : "Unable to load hotels.");
    } finally { setLoading(false); }
  }, [appliedSearch, appliedStatus, router]);

  // Loading remote API state is the synchronization performed by this effect.
  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { void load(); }, [load]);

  async function changeStatus(hotel: Hotel, status: HotelStatus) {
    if (status === hotel.status) return;
    if (["SUSPENDED", "INACTIVE"].includes(status) && !window.confirm(`${status === "SUSPENDED" ? "Suspend" : "Deactivate"} ${hotel.name}? This changes customer-facing availability.`)) return;
    const reason = window.prompt(`Reason for changing ${hotel.name} to ${status}`); if (!reason || reason.trim().length < 5) return;
    try { const updated = await controlService.updateHotel(hotel.id, status, reason); setHotels((items) => items.map((item) => item.id === updated.id ? updated : item)); }
    catch (caught) { setError(caught instanceof ApiError ? caught.message : "Unable to update status."); }
  }
  function applyFilters(event:FormEvent){event.preventDefault();const nextSearch=search.trim();setAppliedSearch(nextSearch);setAppliedStatus(status);const query=new URLSearchParams();if(nextSearch)query.set("search",nextSearch);if(status)query.set("status",status);window.history.replaceState(null,"",query.size?`/hotels?${query}`:"/hotels");}

  return (
    <div className="mx-auto max-w-7xl">
      <div className="mb-7 flex flex-wrap items-center justify-between gap-4"><div><p className="eyebrow">Hotel operations</p><h1 className="page-title">Hotels</h1><p className="page-subtitle">Manage properties, room types, and sellable inventory.</p></div><Link href="/hotels/new" className="btn-primary">Add Hotel</Link></div>
      <form onSubmit={applyFilters} className="panel grid gap-3 sm:grid-cols-[1fr_220px_auto]"><label className="text-sm font-bold">Search hotels<input className="input mt-2" value={search} onChange={event=>setSearch(event.target.value)} placeholder="Name, slug, or city"/></label><label className="text-sm font-bold">Status<select className="input mt-2" value={status} onChange={event=>setStatus(event.target.value as HotelStatus|"")}><option value="">All statuses</option>{HOTEL_STATUSES.map(value=><option key={value}>{value}</option>)}</select></label><button className="btn-primary self-end">Apply filters</button></form><FormError message={error} />
      {loading ? <div className="panel mt-5 text-slate-500">Loading hotels…</div> : hotels.length === 0 ? <div className="panel mt-5 text-center"><h2 className="text-lg font-bold">No hotels yet</h2><p className="mt-2 text-slate-500">Create the first property to begin.</p></div> : (
        <div className="panel mt-5 overflow-x-auto p-0"><table className="min-w-full text-left text-sm"><thead className="border-b bg-slate-50 text-xs uppercase tracking-wide text-slate-500"><tr>{["Hotel", "City", "Type", "Rating", "Status", "Featured", "Created", "Actions"].map((h) => <th key={h} className="px-4 py-3">{h}</th>)}</tr></thead><tbody className="divide-y">{hotels.map((hotel) => <tr key={hotel.id} className="hover:bg-slate-50"><td className="px-4 py-4 font-semibold">{hotel.name}</td><td className="px-4 py-4">{hotel.city}</td><td className="px-4 py-4">{hotel.property_type}</td><td className="px-4 py-4">{hotel.star_rating} ★</td><td className="px-4 py-4"><StatusBadge status={hotel.status} /></td><td className="px-4 py-4">{hotel.is_featured ? "Yes" : "No"}</td><td className="px-4 py-4 whitespace-nowrap">{new Date(hotel.created_at).toLocaleDateString()}</td><td className="px-4 py-4"><div className="flex items-center gap-2"><Link className="link" href={`/hotels/${hotel.id}`}>View</Link><Link className="link" href={`/hotels/${hotel.id}/edit`}>Edit</Link><select aria-label={`Change status for ${hotel.name}`} value={hotel.status} onChange={(e) => void changeStatus(hotel, e.target.value as HotelStatus)} className="rounded-md border border-slate-300 bg-white px-2 py-1 text-xs">{HOTEL_STATUSES.map((s) => <option key={s}>{s}</option>)}</select></div></td></tr>)}</tbody></table></div>
      )}
    </div>
  );
}
