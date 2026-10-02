"use client";

import Link from "next/link";
import { FormEvent, useEffect, useMemo, useState } from "react";

import { partnerService } from "@/src/services/partner.service";
import type { PartnerRoomType, RoomInventoryData } from "@/src/types/partner";

function isoToday() {
  return new Date().toISOString().slice(0, 10);
}

function isoWeekFromToday() {
  const value = new Date();
  value.setDate(value.getDate() + 6);
  return value.toISOString().slice(0, 10);
}

export default function InventoryPage() {
  const [rooms, setRooms] = useState<PartnerRoomType[]>([]);
  const [roomId, setRoomId] = useState<number | null>(null);
  const [startDate, setStartDate] = useState(isoToday);
  const [endDate, setEndDate] = useState(isoWeekFromToday);
  const [items, setItems] = useState<RoomInventoryData[]>([]);
  const [total, setTotal] = useState("");
  const [blocked, setBlocked] = useState("");
  const [price, setPrice] = useState("");
  const [closed, setClosed] = useState<"" | "open" | "closed">("");
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);
  const [message, setMessage] = useState("Loading room types…");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    partnerService.getRoomTypes()
      .then((data) => {
        setRooms(data);
        setRoomId(data[0]?.id ?? null);
        setMessage(data.length ? "" : "Create a room type before managing inventory.");
      })
      .catch((error: Error) => setMessage(error.message));
  }, []);

  useEffect(() => {
    if (!roomId) return;
    partnerService.getRoomInventory(roomId, startDate, endDate)
      .then((result) => {
        setItems(result.items);
        setLastUpdated(result.last_inventory_update);
        setMessage(result.items.length ? "" : "No inventory has been set for this range yet.");
      })
      .catch((error: Error) => setMessage(error.message));
  }, [roomId, startDate, endDate]);

  const room = useMemo(() => rooms.find((item) => item.id === roomId), [rooms, roomId]);

  async function applyUpdate(event: FormEvent) {
    event.preventDefault();
    if (!roomId) return;
    if (!total && !blocked && !price) {
      setMessage("Enter at least one setting to apply.");
      return;
    }
    setSaving(true);
    try {
      const result = await partnerService.updateRoomInventory(roomId, {
        start_date: startDate,
        end_date: endDate,
        ...(total ? { total_inventory: Number(total) } : {}),
        ...(blocked ? { blocked_inventory: Number(blocked) } : {}),
        ...(price ? { price: Number(price) } : {}),
        ...(closed ? { is_closed: closed === "closed" } : {}),
      });
      setItems(result.items);
      setLastUpdated(result.last_inventory_update);
      setMessage("Inventory updated.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Inventory update failed.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <main className="mx-auto max-w-6xl px-5 py-10 text-slate-800">
      <div className="mb-8 flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-sm font-bold uppercase tracking-widest text-blue-700">Partner portal</p>
          <h1 className="mt-1 text-3xl font-black text-[#0b163d]">Room inventory</h1>
          <p className="mt-2 max-w-2xl text-sm text-slate-500">Manage future nightly capacity. Confirmed stays and active booking holds are protected automatically.</p>
        </div>
        <Link href="/partner/room-types" className="rounded-xl border border-slate-300 px-4 py-2 text-sm font-bold hover:bg-white">Room types</Link>
      </div>

      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="grid gap-4 md:grid-cols-3">
          <label className="text-sm font-bold">Room type<select value={roomId ?? ""} onChange={(e) => setRoomId(Number(e.target.value))} className="mt-1 block w-full rounded-lg border border-slate-300 p-2 font-normal"><option value="" disabled>Select a room</option>{rooms.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
          <label className="text-sm font-bold">From<input type="date" min={isoToday()} value={startDate} onChange={(e) => setStartDate(e.target.value)} className="mt-1 block w-full rounded-lg border border-slate-300 p-2 font-normal" /></label>
          <label className="text-sm font-bold">To<input type="date" min={startDate} value={endDate} onChange={(e) => setEndDate(e.target.value)} className="mt-1 block w-full rounded-lg border border-slate-300 p-2 font-normal" /></label>
        </div>
        {room && <p className="mt-4 text-sm text-slate-500">Room-type maximum: <strong>{room.total_rooms}</strong>. New dates default to this total and the room type&apos;s base price.</p>}
      </section>

      <form onSubmit={applyUpdate} className="mt-5 rounded-2xl bg-[#0b163d] p-5 text-white shadow-sm">
        <h2 className="font-bold">Apply settings to the selected date range</h2>
        <div className="mt-4 grid gap-4 md:grid-cols-4">
          <label className="text-sm">Total rooms<input inputMode="numeric" min="0" value={total} onChange={(e) => setTotal(e.target.value)} placeholder="Leave unchanged" className="mt-1 block w-full rounded-lg bg-white p-2 text-slate-900" /></label>
          <label className="text-sm">Blocked / maintenance<input inputMode="numeric" min="0" value={blocked} onChange={(e) => setBlocked(e.target.value)} placeholder="Leave unchanged" className="mt-1 block w-full rounded-lg bg-white p-2 text-slate-900" /></label>
          <label className="text-sm">Nightly price<input inputMode="decimal" min="0" value={price} onChange={(e) => setPrice(e.target.value)} placeholder="Leave unchanged" className="mt-1 block w-full rounded-lg bg-white p-2 text-slate-900" /></label>
          <label className="text-sm">Sales status<select value={closed} onChange={(e) => setClosed(e.target.value as "" | "open" | "closed")} className="mt-1 block w-full rounded-lg bg-white p-2 text-slate-900"><option value="">Leave unchanged</option><option value="open">Open dates</option><option value="closed">Close dates</option></select></label>
        </div>
        <button disabled={saving || !roomId} className="mt-5 rounded-xl bg-white px-5 py-2.5 text-sm font-black text-[#0b163d] disabled:opacity-50">{saving ? "Saving…" : "Apply inventory settings"}</button>
      </form>

      <div className="mt-6 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="flex flex-wrap justify-between gap-2 border-b border-slate-100 px-5 py-4"><h2 className="font-bold text-[#0b163d]">Daily availability</h2><span className="text-xs text-slate-400">Last update: {lastUpdated ? new Date(lastUpdated).toLocaleString() : "—"}</span></div>
        {message && <p className="px-5 py-4 text-sm text-slate-500">{message}</p>}
        {!!items.length && <div className="overflow-x-auto"><table className="w-full min-w-[760px] text-left text-sm"><thead className="bg-slate-50 text-xs uppercase text-slate-500"><tr><th className="p-4">Date</th><th>Total</th><th>Available</th><th>Blocked</th><th>Confirmed</th><th>On hold</th><th>Rate</th><th>Status</th></tr></thead><tbody>{items.map((item) => <tr key={item.id} className="border-t border-slate-100"><td className="p-4 font-semibold">{item.inventory_date}</td><td>{item.total_inventory}</td><td className="font-bold text-emerald-700">{item.available_inventory}</td><td>{item.blocked_inventory}</td><td>{item.confirmed_inventory}</td><td>{item.held_inventory}</td><td>₹{Number(item.price).toLocaleString()}</td><td>{item.is_closed ? "Closed" : "Open"}</td></tr>)}</tbody></table></div>}
      </div>
    </main>
  );
}
