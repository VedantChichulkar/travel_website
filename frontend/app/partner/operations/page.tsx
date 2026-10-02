"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { ApiError } from "@/src/services/api";
import { partnerService } from "@/src/services/partner.service";
import type { CheckInIssueType, OperationBoard, OperationBooking } from "@/src/types/partner";

const ISSUE_TYPES: Array<{ value: CheckInIssueType; label: string }> = [
  { value: "MISSING_OR_INVALID_ID", label: "Missing or invalid required ID" },
  { value: "BOOKING_MISMATCH", label: "Booking details do not match" },
  { value: "OPERATIONAL_VERIFICATION", label: "Other operational verification issue" },
];

const EMPTY_BOARD: OperationBoard = {
  generated_at: "",
  arrivals: [],
  checked_in: [],
  upcoming_checkouts: [],
  no_show_actions: [],
  check_in_issues: [],
};

export default function OperationsPage() {
  const [board, setBoard] = useState<OperationBoard>(EMPTY_BOARD);
  const [selected, setSelected] = useState<OperationBooking | null>(null);
  const [query, setQuery] = useState("");
  const [room, setRoom] = useState("");
  const [issueType, setIssueType] = useState<CheckInIssueType>("MISSING_OR_INVALID_ID");
  const [issue, setIssue] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [unauthorized, setUnauthorized] = useState(false);

  const loadBoard = useCallback(async () => {
    setError("");
    try {
      setBoard(await partnerService.getOperationsBoard());
    } catch (cause) {
      setUnauthorized(cause instanceof ApiError && (cause.status === 401 || cause.status === 403));
      setError(cause instanceof Error ? cause.message : "Hotel operations could not be loaded.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    queueMicrotask(() => void loadBoard());
  }, [loadBoard]);

  async function lookup() {
    const value = query.trim();
    if (!value) return;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const payload = /^\d+$/.test(value)
        ? { booking_id: Number(value) }
        : /^TRV-/i.test(value)
          ? { booking_reference: value.toUpperCase() }
          : { qr_token: value };
      const booking = await partnerService.lookupOperation(payload);
      setSelected(booking);
      setRoom(booking.assigned_room ?? "");
    } catch (cause) {
      setSelected(null);
      setError(cause instanceof Error ? cause.message : "Booking lookup failed.");
    } finally {
      setBusy(false);
    }
  }

  async function perform(action: () => Promise<OperationBooking>, success: string) {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const booking = await action();
      setSelected(booking);
      setNotice(success);
      await loadBoard();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "The operation could not be recorded.");
    } finally {
      setBusy(false);
    }
  }

  function selectBooking(booking: OperationBooking) {
    setSelected(booking);
    setRoom(booking.assigned_room ?? "");
    setIssue("");
    setError("");
    setNotice("");
  }

  if (loading) return <OperationsSkeleton />;
  if (unauthorized) return <UnauthorizedState />;

  return (
    <main className="mx-auto w-full max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <Link href="/partner/dashboard" className="text-sm font-black text-[#172554] hover:underline">← Partner dashboard</Link>
          <p className="mt-6 text-xs font-black uppercase tracking-[.16em] text-[#d95025]">Front desk workspace</p>
          <h1 className="mt-2 text-3xl font-black tracking-tight text-[#0b163d]">Hotel operations</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-500">Verify arrivals, manage active stays, and handle time-sensitive exceptions without exposing payment or contact details.</p>
        </div>
        <button type="button" onClick={() => void loadBoard()} className="secondary-button" disabled={busy}>Refresh board</button>
      </div>

      <section className="mt-7 grid gap-3 sm:grid-cols-2 lg:grid-cols-4" aria-label="Operations summary">
        <Metric label="Today’s arrivals" value={board.arrivals.length} tone="navy" />
        <Metric label="Checked-in guests" value={board.checked_in.length} tone="green" />
        <Metric label="Upcoming checkouts" value={board.upcoming_checkouts.length} tone="blue" />
        <Metric label="No-show actions" value={board.no_show_actions.length} tone="orange" />
      </section>

      <section className="mt-7 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
        <label htmlFor="booking-lookup" className="text-sm font-black text-[#0b163d]">Find a booking</label>
        <p className="mt-1 text-xs text-slate-500">Enter a Maharashtra Tourist Places booking reference, numeric booking ID, or scan and paste the QR token.</p>
        <div className="mt-4 flex flex-col gap-2 sm:flex-row">
          <input id="booking-lookup" className="field-input min-w-0 flex-1" value={query} onChange={(event) => setQuery(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") void lookup(); }} placeholder="TRV-HOT-2026-000123" autoComplete="off" />
          <button className="primary-button sm:min-w-36" disabled={busy || !query.trim()} onClick={() => void lookup()}>{busy ? "Checking…" : "Find booking"}</button>
        </div>
      </section>

      {error && <div role="alert" className="mt-5 rounded-xl border border-red-200 bg-red-50 p-4 text-sm font-semibold text-red-700"><p>{error}</p><button type="button" onClick={() => { setError(""); void loadBoard(); }} className="mt-2 font-black underline">Try again</button></div>}
      {notice && <p role="status" className="mt-5 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm font-semibold text-emerald-700">{notice}</p>}

      {selected && (
        <OperationDetail
          booking={selected}
          room={room}
          issue={issue}
          issueType={issueType}
          busy={busy}
          onRoomChange={setRoom}
          onIssueChange={setIssue}
          onIssueTypeChange={setIssueType}
          onCheckIn={() => void perform(() => partnerService.checkInOperation(selected.id, room.trim()), "Guest checked in successfully.")}
          onCheckOut={() => void perform(() => partnerService.checkOutOperation(selected.id), "Stay checked out successfully.")}
          onIssue={() => void perform(() => partnerService.issueOperation(selected.id, issueType, issue.trim()), "Check-in issue sent for support review.")}
          onNoShow={() => {
            if (window.confirm("Report this confirmed booking as a no-show? This action cannot be repeated.")) {
              void perform(() => partnerService.noShowOperation(selected.id), "No-show recorded using the booking-time policy snapshot.");
            }
          }}
        />
      )}

      <div className="mt-7 grid gap-6 xl:grid-cols-2">
        <OperationSection title="Today’s arrivals" description="Confirmed arrivals and check-in issues scheduled for today." items={board.arrivals} empty="No arrivals are scheduled for today." onSelect={selectBooking} />
        <OperationSection title="Checked-in guests" description="Guests currently staying at the property." items={board.checked_in} empty="No guests are currently checked in." onSelect={selectBooking} />
        <OperationSection title="Upcoming checkouts" description="Active stays ordered by scheduled checkout." items={board.upcoming_checkouts} empty="No upcoming checkouts." onSelect={selectBooking} />
        <OperationSection title="No-show actions" description="Hotel action remains available before Maharashtra Tourist Places’ automatic fallback." items={board.no_show_actions} empty="No no-show decisions need attention." onSelect={selectBooking} />
        <OperationSection title="Support-review issues" description="Check-in issues remain separate from no-show processing." items={board.check_in_issues} empty="No check-in issues are awaiting support review." onSelect={selectBooking} wide />
      </div>
    </main>
  );
}

function Metric({ label, value, tone }: { label: string; value: number; tone: "navy" | "green" | "blue" | "orange" }) {
  const colors = { navy: "bg-[#172554] text-white", green: "bg-emerald-50 text-emerald-900", blue: "bg-sky-50 text-sky-900", orange: "bg-orange-50 text-orange-900" };
  return <article className={`rounded-2xl border border-slate-200 p-5 ${colors[tone]}`}><p className="text-xs font-black uppercase tracking-[.12em] opacity-70">{label}</p><p className="mt-2 text-3xl font-black">{value}</p></article>;
}

function OperationSection({ title, description, items, empty, onSelect, wide = false }: { title: string; description: string; items: OperationBooking[]; empty: string; onSelect: (booking: OperationBooking) => void; wide?: boolean }) {
  return (
    <section className={`rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6 ${wide ? "xl:col-span-2" : ""}`}>
      <h2 className="text-lg font-black text-[#0b163d]">{title}</h2>
      <p className="mt-1 text-xs leading-5 text-slate-500">{description}</p>
      <div className="mt-4 space-y-3">
        {items.map((booking) => <OperationRow key={booking.id} booking={booking} onSelect={() => onSelect(booking)} />)}
        {!items.length && <div className="rounded-xl border border-dashed border-slate-200 p-6 text-center text-sm text-slate-400">{empty}</div>}
      </div>
    </section>
  );
}

function OperationRow({ booking, onSelect }: { booking: OperationBooking; onSelect: () => void }) {
  return (
    <button type="button" onClick={onSelect} className="flex w-full items-center justify-between gap-4 rounded-xl border border-slate-100 p-4 text-left transition hover:border-[#172554]/30 hover:bg-slate-50">
      <span className="min-w-0"><span className="block truncate text-sm font-black text-slate-800">{booking.primary_guest_name ?? "Primary guest"}</span><span className="mt-1 block text-xs text-slate-500">{booking.booking_reference} · {booking.room_snapshot.name ?? "Room"}</span></span>
      <span className="shrink-0 text-right"><Status status={booking.status} system={booking.is_system_generated} /><span className="mt-1 block text-xs text-slate-400">{booking.check_in} → {booking.check_out}</span></span>
    </button>
  );
}

function OperationDetail({ booking, room, issue, issueType, busy, onRoomChange, onIssueChange, onIssueTypeChange, onCheckIn, onCheckOut, onIssue, onNoShow }: { booking: OperationBooking; room: string; issue: string; issueType: CheckInIssueType; busy: boolean; onRoomChange: (value: string) => void; onIssueChange: (value: string) => void; onIssueTypeChange: (value: CheckInIssueType) => void; onCheckIn: () => void; onCheckOut: () => void; onIssue: () => void; onNoShow: () => void }) {
  return (
    <section className="mt-6 rounded-2xl border-2 border-[#172554]/15 bg-white p-5 shadow-sm sm:p-7">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div><p className="text-xs font-black uppercase tracking-[.12em] text-slate-400">{booking.booking_reference}</p><h2 className="mt-2 text-2xl font-black text-[#0b163d]">{booking.primary_guest_name ?? "Primary guest"}</h2><p className="mt-1 text-sm text-slate-500">{booking.room_snapshot.name ?? "Room"} · {booking.rooms} room{booking.rooms === 1 ? "" : "s"} · {booking.check_in} to {booking.check_out}</p></div>
        <Status status={booking.status} system={booking.is_system_generated} />
      </div>
      <dl className="mt-5 grid gap-4 rounded-xl bg-slate-50 p-4 text-sm sm:grid-cols-3">
        <Detail label="Assigned room" value={booking.assigned_room ?? "Not assigned"} />
        <Detail label="Checked in" value={formatTime(booking.checked_in_at)} />
        <Detail label="Checked out" value={formatTime(booking.checked_out_at)} />
      </dl>
      {booking.status_note && <p className="mt-4 rounded-xl border border-slate-200 p-3 text-xs leading-5 text-slate-600">{booking.status_note}</p>}
      {booking.requires_financial_review && <p className="mt-4 rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs font-semibold text-amber-800">Booking-time policy requires Maharashtra Tourist Places support to review the financial implication. No refund was created automatically.</p>}
      {booking.can_check_in && <div className="mt-5 grid gap-3 lg:grid-cols-[1fr_auto]"><input className="field-input" value={room} onChange={(event) => onRoomChange(event.target.value)} placeholder="Physical room label, e.g. A-101" /><button className="primary-button" disabled={busy || !room.trim()} onClick={onCheckIn}>Check in guest</button></div>}
      {booking.can_check_in && <div className="mt-4 grid gap-3 lg:grid-cols-[220px_1fr_auto]"><select className="field-input" value={issueType} onChange={(event) => onIssueTypeChange(event.target.value as CheckInIssueType)}>{ISSUE_TYPES.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select><input className="field-input" value={issue} onChange={(event) => onIssueChange(event.target.value)} placeholder="Describe the verification issue" /><button className="secondary-button" disabled={busy || issue.trim().length < 3} onClick={onIssue}>Send to review</button></div>}
      {booking.can_report_no_show && <button className="mt-4 text-sm font-black text-red-700 underline" disabled={busy} onClick={onNoShow}>Report no-show</button>}
      {booking.can_check_out && <button className="primary-button mt-5" disabled={busy} onClick={onCheckOut}>Check out guest</button>}
      {booking.no_show_reminder_sent_at && booking.status === "CONFIRMED" && <p className="mt-4 text-xs font-semibold text-orange-700">Reminder issued. Hotel action remains available before {formatTime(booking.no_show_eligible_at)}.</p>}
      {booking.auto_checkout_eligible_at && booking.status === "CHECKED_IN" && <p className="mt-4 text-xs text-slate-500">If no action is recorded, Maharashtra Tourist Places will auto-close this stay after {formatTime(booking.auto_checkout_eligible_at)}.</p>}
    </section>
  );
}

function Status({ status, system }: { status: string; system: boolean }) {
  const tone = status === "CHECKED_IN" ? "bg-emerald-100 text-emerald-800" : status === "CHECK_IN_ISSUE" ? "bg-orange-100 text-orange-800" : status === "NO_SHOW" ? "bg-red-100 text-red-800" : status === "CHECKED_OUT" ? "bg-sky-100 text-sky-800" : "bg-slate-100 text-slate-700";
  return <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-black ${tone}`}>{system ? "Maharashtra Tourist Places · " : ""}{status.replaceAll("_", " ")}</span>;
}

function Detail({ label, value }: { label: string; value: string }) { return <div><dt className="text-xs font-black uppercase tracking-wide text-slate-400">{label}</dt><dd className="mt-1 font-bold text-slate-700">{value}</dd></div>; }
function formatTime(value: string | null) { return value ? new Intl.DateTimeFormat("en-IN", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value)) : "Not recorded"; }

function OperationsSkeleton() { return <main className="mx-auto w-full max-w-7xl px-4 py-10"><div className="skeleton h-10 w-72 rounded-xl" /><div className="mt-7 grid gap-3 sm:grid-cols-4">{[1, 2, 3, 4].map((item) => <div key={item} className="skeleton h-28 rounded-2xl" />)}</div><div className="skeleton mt-7 h-44 rounded-2xl" /><div className="mt-7 grid gap-6 lg:grid-cols-2"><div className="skeleton h-72 rounded-2xl" /><div className="skeleton h-72 rounded-2xl" /></div></main>; }
function UnauthorizedState() { return <main className="grid min-h-[70vh] place-items-center px-5"><section className="max-w-md rounded-2xl border border-red-200 bg-white p-8 text-center"><h1 className="text-2xl font-black text-[#0b163d]">Partner access required</h1><p className="mt-3 text-sm text-slate-500">Your session cannot access this hotel’s operations workspace.</p><Link href="/partner/login" className="primary-button mt-6">Return to partner login</Link></section></main>; }
