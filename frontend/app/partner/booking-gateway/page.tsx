"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { partnerService } from "@/src/services/partner.service";
import type { BookingGatewayState, BookingGatewayStatus } from "@/src/types/partner";

const label = (value: string) => value.replaceAll("_", " ").toLowerCase().replace(/\b\w/g, (letter) => letter.toUpperCase());

export default function BookingGatewayPage() {
  const [gateway, setGateway] = useState<BookingGatewayState | null>(null);
  const [message, setMessage] = useState("Loading booking gateway…");
  const [saving, setSaving] = useState(false);
  useEffect(() => { partnerService.getBookingGateway().then((state) => { setGateway(state); setMessage(""); }).catch((error: Error) => setMessage(error.message)); }, []);
  async function change(status: BookingGatewayStatus) {
    setSaving(true); setMessage("");
    try { setGateway(await partnerService.updateBookingGateway(status)); }
    catch (error) { setMessage(error instanceof Error ? error.message : "Could not update booking mode."); }
    finally { setSaving(false); }
  }
  return <main className="mx-auto max-w-3xl px-5 py-10 text-slate-800"><Link href="/partner/dashboard" className="text-sm font-bold text-[#172554]">← Partner dashboard</Link><h1 className="mt-4 text-3xl font-black text-[#0b163d]">Booking gateway</h1><p className="mt-2 text-slate-500">Choose how new stays reach your hotel. This never affects confirmed bookings.</p>{message && <p className="mt-6 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm font-semibold text-amber-800">{message}</p>}{gateway && <><section className="mt-6 grid gap-3 sm:grid-cols-3"><div className="rounded-xl bg-[#0b163d] p-4 text-white"><p className="text-xs font-bold uppercase">Effective mode</p><p className="mt-2 font-black">{label(gateway.effective_status)}</p></div><div className="rounded-xl border bg-white p-4"><p className="text-xs font-bold uppercase text-slate-400">Inventory</p><p className="mt-2 font-black">{gateway.inventory_is_fresh ? "Fresh" : "Needs attention"}</p><p className="mt-1 text-xs text-slate-500">{gateway.inventory_last_updated_at ? new Date(gateway.inventory_last_updated_at).toLocaleString() : "No update yet"}</p></div><div className="rounded-xl border bg-white p-4"><p className="text-xs font-bold uppercase text-slate-400">Verification</p><p className="mt-2 font-black">{gateway.verified ? "Verified" : "Not verified"}</p></div></section>{gateway.override_status && <section className="mt-5 rounded-xl border border-rose-200 bg-rose-50 p-4"><p className="font-black text-rose-900">Maharashtra Tourist Places override: {label(gateway.override_status)}</p><p className="mt-1 text-sm text-rose-800">{gateway.override_reason}</p></section>}{gateway.inventory_freshness_reason && <p className="mt-5 rounded-xl bg-amber-50 p-4 text-sm font-semibold text-amber-800">{gateway.inventory_freshness_reason}</p>}<section className="mt-6 rounded-2xl border bg-white p-6"><h2 className="font-black text-[#0b163d]">Your preferred mode</h2><div className="mt-4 grid gap-3">{(["ACTIVE", "BOOKING_ON_REQUEST", "PAUSED"] as BookingGatewayStatus[]).map((status) => <button key={status} disabled={saving || Boolean(gateway.override_status)} onClick={() => void change(status)} className={`rounded-xl border p-4 text-left ${gateway.partner_requested_status === status ? "border-[#172554] bg-blue-50" : "border-slate-200"} disabled:opacity-50`}><strong>{label(status)}</strong><span className="mt-1 block text-sm text-slate-500">{status === "ACTIVE" ? "Confirm instantly when verification and inventory freshness allow." : status === "BOOKING_ON_REQUEST" ? "Accept new stays as requests for manual confirmation." : "Stop accepting new stays without affecting confirmed bookings."}</span></button>)}</div></section></>}</main>;
}
