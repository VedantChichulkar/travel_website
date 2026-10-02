"use client";

import { useCallback, useEffect, useState } from "react";
import { AdminShell } from "@/components/AdminShell";
import { safariService, type SafariRequest, type SafariStatus } from "@/services/safari.service";

const filters: Array<SafariStatus | "ALL"> = [
  "AVAILABILITY_REQUESTED", "CHECKING_AVAILABILITY", "AWAITING_TRAVELLER_DETAILS", "PAYMENT_PENDING",
  "BOOKING_IN_PROGRESS", "CONFIRMED", "NOT_AVAILABLE", "BOOKING_FAILED", "ALL",
];
const PRIVATE_DOCUMENT_MAX_BYTES = 10 * 1024 * 1024;

export default function SafariOperationsPage() {
  return <AdminShell><Content /></AdminShell>;
}

function Content() {
  const [items, setItems] = useState<SafariRequest[]>([]);
  const [filter, setFilter] = useState<SafariStatus | "ALL">("AVAILABILITY_REQUESTED");
  const [overdue, setOverdue] = useState(false);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState<number>();
  const load = useCallback(async () => {
    try { setItems(await safariService.list(filter === "ALL" ? undefined : filter, overdue)); }
    catch { setMessage("Could not load safari operations."); }
  }, [filter, overdue]);
  useEffect(() => { queueMicrotask(() => { void load(); }); }, [load]);

  async function run(item: SafariRequest, action: () => Promise<unknown>) {
    setBusy(item.id);
    try { await action(); setMessage("Safari operation saved."); await load(); }
    catch (error) { setMessage(error instanceof Error ? error.message : "Operation failed."); }
    finally { setBusy(undefined); }
  }
  function reason(label: string) { return window.prompt(`${label} reason (required):`)?.trim() || ""; }
  function uploadConfirmation(item: SafariRequest, file: File) {
    if (file.size > PRIVATE_DOCUMENT_MAX_BYTES) { setMessage("The private document must be 10 MB or smaller."); return; }
    void run(item, () => safariService.uploadConfirmation(item.id, file, "official_ticket_or_permit"));
  }
  function markUnavailable(item: SafariRequest) {
    const value = reason("Mark unavailable");
    if (!value) return;
    const safariDate = window.prompt("Optional alternative date (YYYY-MM-DD), or leave blank:")?.trim();
    const shift = safariDate ? window.prompt("Alternative shift (optional):")?.trim() : undefined;
    const note = safariDate ? window.prompt("Alternative note (optional):")?.trim() : undefined;
    const bookingCategory = safariDate && item.safari.booking_categories.length ? window.prompt("Alternative booking category code (optional):")?.trim() : undefined;
    const vehicleOption = safariDate && item.safari.vehicle_options.length ? window.prompt("Alternative vehicle option code (optional):")?.trim() : undefined;
    const alternatives = safariDate ? [{ safari_date: safariDate, shift: shift || undefined, booking_category: bookingCategory || undefined, vehicle_option: vehicleOption || undefined, note: note || undefined }] : [];
    void run(item, () => safariService.availability(item.id, "MARK_UNAVAILABLE", value, alternatives));
  }
  function recordOfficialConfirmation(item: SafariRequest) {
    const bookingReference = window.prompt(`Official booking reference${item.safari.official_reference_required ? " (required)" : " (optional)"}:`)?.trim();
    const safariDate = window.prompt("Final safari date (YYYY-MM-DD):", item.preferred_date)?.trim();
    const shift = window.prompt("Final shift (optional):", item.preferred_shift || "")?.trim();
    const zone = window.prompt("Final zone (optional):")?.trim();
    const gate = window.prompt("Final gate (optional):")?.trim();
    const bookingCategory = item.safari.booking_categories.length ? window.prompt("Confirmed booking category code:", item.preferred_booking_category || "")?.trim() : undefined;
    const vehicleOption = item.safari.vehicle_options.length ? window.prompt("Confirmed vehicle option code:", item.preferred_vehicle_option || "")?.trim() : undefined;
    const officialContact = window.prompt(`Registered official booking contact${item.safari.official_contact_required ? " (required)" : " (optional)"}:`)?.trim();
    const instructions = window.prompt("Reporting instructions:")?.trim();
    const value = reason("Confirm booking");
    if ((!item.safari.official_reference_required || bookingReference) && (!item.safari.official_contact_required || officialContact) && safariDate && instructions && value && item.payable_amount) {
      void run(item, () => safariService.confirm(item.id, { booking_reference: bookingReference || undefined, safari_date: safariDate, shift: shift || undefined, zone: zone || undefined, gate: gate || undefined, booking_category: bookingCategory || undefined, vehicle_option: vehicleOption || undefined, official_booking_contact: officialContact || undefined, reporting_instructions: instructions, final_amount: item.payable_amount, reason: value }));
    }
  }

  return <div className="mx-auto max-w-7xl">
    <p className="text-sm font-bold uppercase tracking-wider text-indigo-700">Managed bookings</p>
    <h1 className="mt-1 text-3xl font-bold">Safari Operations</h1>
    <p className="mt-2 text-slate-500">Manual availability, traveller readiness, pricing, external booking, confirmation, and payment-exception queues.</p>
    <div className="mt-6 flex flex-wrap gap-2">
      {filters.map((value) => <button key={value} onClick={() => setFilter(value)} className={`rounded-lg px-3 py-2 text-xs font-bold ${filter === value ? "bg-indigo-600 text-white" : "border bg-white"}`}>{value.replaceAll("_", " ")}</button>)}
      <button onClick={() => setOverdue((value) => !value)} className={`rounded-lg px-3 py-2 text-xs font-bold ${overdue ? "bg-red-600 text-white" : "border bg-white text-red-700"}`}>Overdue only</button>
    </div>
    {message && <p className="mt-4 rounded-lg bg-blue-50 p-3 text-sm text-blue-800">{message}</p>}
    <div className="mt-6 space-y-4">{items.map((item) => <article key={item.id} className="rounded-2xl border bg-white p-5 shadow-sm">
      <div className="flex flex-wrap justify-between gap-3"><div><h2 className="font-bold">{item.safari.name} · {item.request_reference}</h2><p className="text-sm text-slate-500">{item.preferred_date} {item.preferred_shift} · {item.visitor_count} visitors{item.preferred_booking_category ? ` · ${item.preferred_booking_category}` : ""}{item.preferred_vehicle_option ? ` · ${item.preferred_vehicle_option}` : ""}</p>{item.safari.source_url && <a href={item.safari.source_url} target="_blank" rel="noreferrer" className="mt-1 inline-flex text-xs font-bold text-indigo-700 underline">Open configured official source</a>}</div><span className={`h-fit rounded-full px-3 py-1 text-xs font-bold ${item.overdue ? "bg-red-100 text-red-800" : "bg-slate-100"}`}>{item.status.replaceAll("_", " ")}{item.overdue ? " · SLA OVERDUE" : ""}</span></div>
      <div className="mt-4 grid gap-3 text-sm sm:grid-cols-4"><p><b>Target</b><br />{new Date(item.target_response_at).toLocaleString()}</p><p><b>Payment</b><br />{item.payment_status}</p><p><b>Amount</b><br />{item.currency} {item.payable_amount}</p><p><b>Reconciliation</b><br />{item.refund_status || item.payment_reconciliation_status || "—"}</p></div>
      <div className="mt-4 flex flex-wrap gap-2">
        {item.status === "AVAILABILITY_REQUESTED" && <button disabled={busy === item.id} onClick={() => { const value = reason("Start check"); if (value) void run(item, () => safariService.availability(item.id, "START_CHECK", value)); }} className="rounded-lg bg-indigo-600 px-3 py-2 text-xs font-bold text-white">Start check</button>}
        {["AVAILABILITY_REQUESTED", "CHECKING_AVAILABILITY"].includes(item.status) && <><button disabled={busy === item.id} onClick={() => { const value = reason("Mark available"); if (value) void run(item, () => safariService.availability(item.id, "MARK_AVAILABLE", value)); }} className="rounded-lg bg-emerald-600 px-3 py-2 text-xs font-bold text-white">Mark available</button><button disabled={busy === item.id} onClick={() => markUnavailable(item)} className="rounded-lg bg-red-600 px-3 py-2 text-xs font-bold text-white">Mark unavailable</button></>}
        {["AWAITING_TRAVELLER_DETAILS", "DETAILS_SUBMITTED", "PAYMENT_PENDING"].includes(item.status) && <button disabled={busy === item.id} onClick={() => { const amount = window.prompt("Authoritative amount:")?.trim(); const currency = window.prompt("Currency:", "INR")?.trim(); const value = reason("Confirm pricing"); if (amount && currency && value) void run(item, () => safariService.pricing(item.id, amount, currency, { managed_safari: amount }, value)); }} className="rounded-lg bg-amber-600 px-3 py-2 text-xs font-bold text-white">Set price</button>}
        {item.status === "BOOKING_IN_PROGRESS" && <><label title="PDF, JPEG, or PNG; maximum 10 MB" className="cursor-pointer rounded-lg border border-indigo-200 bg-indigo-50 px-3 py-2 text-xs font-bold text-indigo-800">Upload ticket / permit<input type="file" accept="application/pdf,image/jpeg,image/png" className="sr-only" disabled={busy === item.id} onChange={(event) => { const file = event.target.files?.[0]; if (file) uploadConfirmation(item, file); }} /></label><button disabled={busy === item.id} onClick={() => recordOfficialConfirmation(item)} className="rounded-lg bg-emerald-700 px-3 py-2 text-xs font-bold text-white">Record official confirmation</button><button disabled={busy === item.id} onClick={() => { const value = reason("Booking failed"); if (value) void run(item, () => safariService.fail(item.id, value)); }} className="rounded-lg bg-red-700 px-3 py-2 text-xs font-bold text-white">Booking failed</button></>}
      </div>
      {item.confirmation_documents.length > 0 && <p className="mt-3 rounded-lg bg-emerald-50 p-3 text-sm text-emerald-800"><b>Secure booking artifacts:</b> {item.confirmation_documents.map((document) => document.document_type.replaceAll("_", " ")).join(", ")}</p>}
      {item.failure_reason && <p className="mt-3 rounded-lg bg-red-50 p-3 text-sm text-red-800">{item.failure_reason}</p>}
    </article>)}</div>
  </div>;
}
