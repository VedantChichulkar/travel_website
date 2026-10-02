"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useRef, useState } from "react";

import { StatePanel } from "@/src/components/StatePanel";
import { hotelSearchQuery } from "@/src/lib/hotel-search";
import { openPaymentCheckout } from "@/src/lib/payment-checkout";
import { ApiError } from "@/src/services/api";
import { bookingService, type BookingQuote, type CustomerBooking, type InventoryHold, type PaymentOrder, type TravellerInput } from "@/src/services/booking.service";
import { hotelService } from "@/src/services/hotel.service";
import type { HotelDetail, HotelSearchParams, RoomAvailability } from "@/src/types/hotel";

type TravellerDraft = { full_name: string; age: string };

function quoteFingerprint(quote: BookingQuote): string {
  return JSON.stringify({ nightly_prices: quote.nightly_prices, subtotal: quote.subtotal, taxes: quote.taxes, platform_fee: quote.platform_fee, discount: quote.discount, total_amount: quote.total_amount, booking_mode: quote.booking_mode });
}

function bookingError(cause: unknown): string {
  if (cause instanceof ApiError && cause.status === 401) return "Your session has expired. Sign in again before reserving.";
  if (cause instanceof ApiError && cause.status === 409 && cause.message.toLowerCase().includes("expired")) return "Your temporary room hold expired. Return to the room list and reserve again.";
  if (cause instanceof ApiError && cause.status === 409) return "The room or live price changed before the booking could be completed. Return to the room list and check availability again.";
  return "The booking request could not be completed. No new payment or booking is confirmed; please try again.";
}

function formatQuotedMoney(value: string, currency: string): string {
  return new Intl.NumberFormat("en-IN", { style: "currency", currency, minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(Number(value));
}

export function BookingReview({ hotelId, roomId, search }: { hotelId: number; roomId: number; search: HotelSearchParams }) {
  const stay = { hotel_id: hotelId, room_type_id: roomId, check_in: search.checkIn, check_out: search.checkOut, rooms: search.rooms, adults: search.adults, children: search.children };
  const [hotel, setHotel] = useState<HotelDetail | null>(null);
  const [room, setRoom] = useState<RoomAvailability | null>(null);
  const [quote, setQuote] = useState<BookingQuote | null>(null);
  const [hold, setHold] = useState<InventoryHold | null>(null);
  const [booking, setBooking] = useState<CustomerBooking | null>(null);
  const [payment, setPayment] = useState<PaymentOrder | null>(null);
  const [travellers, setTravellers] = useState<TravellerDraft[]>(() => Array.from({ length: search.adults + search.children }, () => ({ full_name: "", age: "" })));
  const [error, setError] = useState("");
  const [authRequired, setAuthRequired] = useState(false);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const idempotencyKey = useRef("");

  useEffect(() => {
    if (!idempotencyKey.current) idempotencyKey.current = `web-${crypto.randomUUID().replaceAll("-", "")}`;
    let active = true;
    void Promise.all([hotelService.getHotel(hotelId), hotelService.getHotelRooms(hotelId, search), bookingService.quote(stay)])
      .then(([detail, availability, liveQuote]) => {
        const selected = availability.items.find((item) => item.id === roomId);
        if (!selected) throw new Error("The selected room is no longer available or approved for booking.");
        if (active) { setHotel(detail); setRoom(selected); setQuote(liveQuote); }
      })
      .catch((cause: unknown) => {
        if (!active) return;
        setAuthRequired((cause instanceof ApiError && cause.status === 401) || (cause instanceof Error && cause.message.includes("sign in")));
        setError(bookingError(cause));
      })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
    // The page key is derived from these immutable stay inputs.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hotelId, roomId, search]);

  const refreshStatus = useCallback(async () => {
    if (!booking) return;
    try {
      const [latestBooking, history] = await Promise.all([bookingService.getBooking(booking.id), bookingService.getPaymentHistory(booking.id)]);
      setBooking(latestBooking);
      setPayment(history.items[0] ?? null);
      setError("");
    } catch (cause) {
      setAuthRequired(cause instanceof ApiError && cause.status === 401);
      setError(bookingError(cause));
    }
  }, [booking]);

  useEffect(() => {
    if (!booking || booking.status !== "PAYMENT_PENDING") return;
    const timer = window.setInterval(() => void refreshStatus(), 5000);
    return () => window.clearInterval(timer);
  }, [booking, refreshStatus]);

  function updateTraveller(index: number, field: keyof TravellerDraft, value: string) {
    setTravellers((current) => current.map((traveller, itemIndex) => itemIndex === index ? { ...traveller, [field]: value } : traveller));
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!quote || !hotel) return;
    const normalized: TravellerInput[] = travellers.map((traveller, index) => ({ full_name: traveller.full_name.trim().replace(/\s+/g, " "), age: Number(traveller.age), is_primary: index === 0 }));
    if (normalized.some((traveller) => traveller.full_name.length < 2 || !Number.isInteger(traveller.age) || traveller.age < 0 || traveller.age > 120)) {
      setError("Enter a valid full name and age from 0 to 120 for every traveller.");
      return;
    }
    setBusy(true);
    setError("");
    setAuthRequired(false);
    try {
      const refreshedQuote = await bookingService.quote(stay);
      if (quoteFingerprint(refreshedQuote) !== quoteFingerprint(quote)) {
        setQuote(refreshedQuote);
        setError("The live price or booking mode changed. Review the updated total, then submit again.");
        return;
      }
      const activeHold = await bookingService.createHold(stay);
      setHold(activeHold);
      const created = await bookingService.createBooking({ ...stay, hold_token: activeHold.hold_token, idempotency_key: idempotencyKey.current, travellers: normalized });
      setBooking(created);
      if (created.status === "PAYMENT_PENDING") {
        const order = await bookingService.createPaymentOrder(created.id);
        setPayment(order);
        if (order.provider === "RAZORPAY") setPayment(await openPaymentCheckout(order, `Hotel booking ${created.booking_reference}`));
      }
    } catch (cause) {
      setAuthRequired((cause instanceof ApiError && cause.status === 401) || (cause instanceof Error && cause.message.includes("sign in")));
      setError(bookingError(cause));
    } finally {
      setBusy(false);
    }
  }

  async function retryPaymentOrder() {
    if (!booking) return;
    setBusy(true);
    setError("");
    try {
      const order = await bookingService.createPaymentOrder(booking.id);
      setPayment(order);
      if (order.provider === "RAZORPAY") setPayment(await openPaymentCheckout(order, `Hotel booking ${booking.booking_reference}`));
    }
    catch (cause) { setError(bookingError(cause)); }
    finally { setBusy(false); }
  }

  if (loading) return <div className="container-shell py-14"><StatePanel title="Preparing your selection" message="Rechecking approval, live inventory, and the backend price…" loading /></div>;
  if ((!hotel || !room || !quote) && error) return <div className="container-shell py-14"><StatePanel title="Selection unavailable" message={error} />{authRequired && <p className="mt-5 text-center"><Link className="primary-button" href="/login">Sign in</Link></p>}</div>;
  if (!hotel || !room || !quote) return null;

  const reconciliationOpen = payment && ["CONFIRMATION_REQUIRED", "REFUND_REQUIRED", "MANUAL_REVIEW"].includes(payment.reconciliation_status);
  const paymentFailed = booking?.payment_status === "FAILED" || payment?.status === "FAILED";
  const confirmed = booking?.status === "CONFIRMED";
  const requested = booking?.status === "PENDING";
  const terminal = confirmed || requested || Boolean(reconciliationOpen);

  return <main className="container-shell py-10">
    <Link href={`/hotels/${hotel.slug}?${hotelSearchQuery(search)}#rooms`} className="text-sm font-black text-[var(--accent)] hover:text-[var(--accent-strong)]">← Back to room choices</Link>
    <p className="eyebrow mt-7">Traveller details · Review · Payment</p>
    <h1 className="page-title mt-3">Complete your stay</h1>

    {booking && <section aria-live="polite" className={`mt-7 rounded-2xl border p-5 ${confirmed ? "border-emerald-200 bg-emerald-50" : reconciliationOpen ? "border-amber-300 bg-amber-50" : paymentFailed ? "border-red-200 bg-red-50" : "border-blue-200 bg-blue-50"}`}>
      <p className="text-xs font-black tracking-[.16em]">{confirmed ? "CONFIRMED" : requested ? "PENDING · BOOKING ON REQUEST" : reconciliationOpen ? payment.reconciliation_status : paymentFailed ? "PAYMENT FAILED · FAILED" : payment?.status === "PENDING" ? "PROCESSING" : "PAYMENT_PENDING"}</p>
      <h2 className="mt-2 text-xl font-black text-[var(--brand-strong)]">Booking {booking.booking_reference}</h2>
      <p className="mt-2 text-sm text-slate-600">{confirmed ? "Your verified payment has been matched and the room is confirmed." : requested ? "The hotel must review this booking-on-request. No payment has been requested and this is not yet confirmed." : reconciliationOpen ? "Payment was verified, but room confirmation needs reconciliation. Do not pay again; Maharashtra Tourist Places operations must confirm fulfilment or flag the payment for refund." : paymentFailed ? "The payment attempt failed. Your booking is not confirmed." : "A server-created payment order exists. Maharashtra Tourist Places is waiting for verified provider evidence; the browser cannot mark it paid."}</p>
      {payment && <p className="mt-2 break-all text-xs text-slate-500">Provider order: {payment.provider_order_id}</p>}
      {!terminal && <div className="mt-4 flex flex-wrap gap-3"><button type="button" className="secondary-button !min-h-10" onClick={() => void refreshStatus()}>Check payment status</button>{payment?.status === "PENDING" && payment.provider === "RAZORPAY" && <button type="button" className="primary-button !min-h-10" disabled={busy} onClick={() => void retryPaymentOrder()}>{busy ? "Opening…" : "Open secure checkout"}</button>}{paymentFailed && <button type="button" className="primary-button !min-h-10" disabled={busy} onClick={() => void retryPaymentOrder()}>{busy ? "Retrying…" : "Create another payment attempt"}</button>}{!payment && <button type="button" className="primary-button !min-h-10" disabled={busy} onClick={() => void retryPaymentOrder()}>{busy ? "Creating…" : "Create payment order"}</button>}</div>}
      {error && <p role="alert" className="mt-4 rounded-xl bg-white/70 p-3 text-sm font-semibold text-red-700">{error}{authRequired && <> <Link className="underline" href="/login">Sign in again</Link>.</>}</p>}
    </section>}

    <div className="mt-8 grid items-start gap-6 lg:grid-cols-[1.35fr_.75fr]">
      <div className="space-y-6">
        <section className="content-card"><p className="eyebrow">Stay selection</p><h2 className="mt-3 text-2xl font-black">{hotel.name} · {room.name}</h2><dl className="mt-5 grid gap-4 text-sm sm:grid-cols-2"><Summary label="Dates" value={`${search.checkIn} — ${search.checkOut}`} /><Summary label="Length" value={`${quote.nights} night${quote.nights === 1 ? "" : "s"}`} /><Summary label="Guests" value={`${search.adults} adults, ${search.children} children`} /><Summary label="Rooms" value={String(search.rooms)} /><Summary label="Booking mode" value={quote.booking_mode === "ACTIVE" ? "Instant booking" : "Booking on request"} /></dl></section>

        {!booking && <form onSubmit={(event) => void submit(event)} className="content-card"><p className="eyebrow">Traveller details</p><h2 className="mt-3 text-2xl font-black">Who is staying?</h2><p className="mt-2 text-sm text-slate-500">Add one traveller for each adult and child. The first traveller is the primary guest.</p><div className="mt-6 grid gap-5">{travellers.map((traveller, index) => <fieldset key={index} className="grid gap-4 rounded-xl border border-slate-200 p-4 sm:grid-cols-[1fr_120px]"><legend className="px-2 text-sm font-black">Traveller {index + 1}{index === 0 ? " · Primary" : ""}</legend><label className="text-sm font-bold">Full name<input className="field-input mt-2" required minLength={2} maxLength={100} autoComplete={index === 0 ? "name" : "off"} value={traveller.full_name} onChange={(event) => updateTraveller(index, "full_name", event.target.value)} /></label><label className="text-sm font-bold">Age<input className="field-input mt-2" required type="number" min={0} max={120} step={1} inputMode="numeric" value={traveller.age} onChange={(event) => updateTraveller(index, "age", event.target.value)} /></label></fieldset>)}</div>{error && <p role="alert" className="mt-5 rounded-xl bg-red-50 p-3 text-sm font-semibold text-red-700">{error}{authRequired && <> <Link className="underline" href="/login">Sign in again</Link>.</>}</p>}<button className="primary-button mt-6 w-full" disabled={busy || quote.booking_mode === "PAUSED"}>{busy ? "Rechecking and reserving…" : quote.booking_mode === "BOOKING_ON_REQUEST" ? "Submit booking request" : quote.booking_mode === "PAUSED" ? "Booking unavailable" : "Reserve and continue to payment"}</button><p className="mt-3 text-xs text-slate-500">The price is rechecked before a temporary hold is created. Submitting twice uses the same booking idempotency key.</p></form>}

        {hotel.policy && <section className="content-card"><p className="eyebrow">Policies captured with booking</p><div className="mt-4 grid gap-4">{Object.entries(hotel.policy).filter(([, value]) => value).map(([key, value]) => <div key={key}><h3 className="text-sm font-black capitalize">{key.replaceAll("_", " ")}</h3><p className="mt-1 text-sm leading-6 text-slate-600">{value}</p></div>)}</div></section>}
      </div>

      <aside className="content-card lg:sticky lg:top-24"><p className="eyebrow">Live quote</p><h2 className="mt-3 text-xl font-black">Price breakdown</h2><div className="mt-5 space-y-3 text-sm">{quote.nightly_prices.map((night) => <PriceRow key={night.date} label={`${night.date} · ${night.rooms} room${night.rooms === 1 ? "" : "s"}`} value={formatQuotedMoney(night.amount, quote.currency)} />)}<hr className="border-slate-200" /><PriceRow label="Subtotal" value={formatQuotedMoney(quote.subtotal, quote.currency)} /><PriceRow label="Taxes" value={formatQuotedMoney(quote.taxes, quote.currency)} /><PriceRow label="Platform fee" value={formatQuotedMoney(quote.platform_fee, quote.currency)} /><PriceRow label="Discount" value={`− ${formatQuotedMoney(quote.discount, quote.currency)}`} /></div><div className="mt-5 flex items-end justify-between border-t border-slate-200 pt-5"><strong>Total</strong><strong className="text-3xl text-[var(--brand-strong)]">{formatQuotedMoney(quote.total_amount, quote.currency)}</strong></div><div className="mt-5 rounded-xl bg-[var(--accent-soft)] p-4 text-sm text-[var(--brand)]"><strong className="block">Temporary inventory hold</strong>{hold ? `Held until ${new Date(hold.expires_at).toLocaleTimeString()}.` : "Created only after traveller validation and a final price check. No payment is taken by a hold."}</div></aside>
    </div>
  </main>;
}

function Summary({ label, value }: { label: string; value: string }) { return <div><dt className="text-slate-500">{label}</dt><dd className="mt-1 font-black text-slate-800">{value}</dd></div>; }
function PriceRow({ label, value }: { label: string; value: string }) { return <div className="flex justify-between gap-4"><span className="text-slate-500">{label}</span><strong className="text-right">{value}</strong></div>; }
