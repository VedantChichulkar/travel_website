"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { Header } from "@/src/components/account/AccountDashboard";
import { ApiError } from "@/src/services/api";
import { date } from "@/src/lib/account-status";
import { bookingService, type CustomerBooking, type ReviewData } from "@/src/services/booking.service";

interface ReviewStay { booking: CustomerBooking; review: ReviewData | null }
export function ReviewList() {
  const [items, setItems] = useState<ReviewStay[]>([]); const [loading, setLoading] = useState(true); const [error, setError] = useState("");
  const load = useCallback(async () => { setLoading(true); setError(""); try { const completed = (await bookingService.listMine()).items.filter((item) => item.status === "CHECKED_OUT"); const rows = await Promise.all(completed.map(async (booking) => ({ booking, review: await bookingService.getReview(booking.id).catch((cause) => cause instanceof ApiError && cause.status === 404 ? null : Promise.reject(cause)) }))); setItems(rows); } catch (cause) { setError(cause instanceof Error ? cause.message : "Review eligibility could not be loaded."); } finally { setLoading(false); } }, []);
  useEffect(() => { queueMicrotask(() => void load()); }, [load]);
  const eligible = items.filter((item) => !item.review); const submitted = items.filter((item) => item.review);
  return <div><Header eyebrow="Your account" title="Verified stay reviews" description="Review eligibility comes from completed Maharashtra Tourist Places stays. Moderation and property responses remain part of the existing review system." />{error && <p role="alert" className="mb-5 rounded-xl bg-red-50 p-4 text-sm text-red-800">{error} <button onClick={() => void load()} className="font-black underline">Try again</button></p>}{loading ? <div className="skeleton h-64 rounded-2xl" /> : <div className="space-y-8"><ReviewSection title="Eligible to review" empty="No completed stays are currently eligible for a new review.">{eligible.map(({ booking }) => <Stay key={booking.booking_reference} booking={booking}><Link href={`/account/reviews/${booking.booking_reference}`} className="primary-button !min-h-10">Write review</Link></Stay>)}</ReviewSection><ReviewSection title="Submitted reviews" empty="No submitted verified-stay reviews yet.">{submitted.map(({ booking, review }) => <Stay key={booking.booking_reference} booking={booking}><div className="text-right"><strong className="block">{review?.overall_rating} / 5</strong><span className="text-xs text-slate-500">{review?.moderation_status.replaceAll("_", " ")}</span><Link href={`/account/reviews/${booking.booking_reference}`} className="mt-2 block text-sm font-black text-[var(--accent)]">View review</Link></div></Stay>)}</ReviewSection></div>}</div>;
}
function ReviewSection({ title, empty, children }: { title: string; empty: string; children: React.ReactNode[] }) { return <section><h2 className="text-xl font-black text-[var(--brand)]">{title}</h2><div className="mt-4 space-y-3">{children.length ? children : <p className="content-card text-sm text-slate-500">{empty}</p>}</div></section>; }
function Stay({ booking, children }: { booking: CustomerBooking; children: React.ReactNode }) { return <article className="content-card flex flex-wrap items-center justify-between gap-5"><div><p className="text-xs font-black uppercase tracking-wide text-[var(--accent)]">{booking.booking_reference}</p><h3 className="mt-2 text-lg font-black text-[var(--brand)]">{booking.hotel.name}</h3><p className="mt-1 text-sm text-slate-500">Stayed {date(booking.check_in)} – {date(booking.check_out)}</p></div>{children}</article>; }
