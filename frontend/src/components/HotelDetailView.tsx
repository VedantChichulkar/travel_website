"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";

import { StatePanel } from "@/src/components/StatePanel";
import { MediaImage } from "@/src/components/MediaImage";
import { formatMoney, hotelSearchQuery, validateStaySelection } from "@/src/lib/hotel-search";
import { hotelService, type PublicReviewList } from "@/src/services/hotel.service";
import type { BookingGatewayStatus, HotelDetail, HotelSearchParams, RoomAvailability, RoomAvailabilityResponse } from "@/src/types/hotel";

export function HotelDetailView({ hotelRef, search }: { hotelRef: string; search: HotelSearchParams }) {
  const [hotel, setHotel] = useState<HotelDetail | null>(null);
  const [availability, setAvailability] = useState<RoomAvailabilityResponse | null>(null);
  const [reviews, setReviews] = useState<PublicReviewList | null>(null);
  const [error, setError] = useState("");
  const [availabilityError, setAvailabilityError] = useState("");
  const validation = validateStaySelection(search);

  useEffect(() => {
    let active = true;
    void Promise.all([hotelService.getHotel(hotelRef), hotelService.getReviews(hotelRef)]).then(([detail, reviewData]) => {
      if (active) { setHotel(detail); setReviews(reviewData); }
    }).catch(() => { if (active) setError("This hotel could not be loaded right now. Return to the stay search and try again."); });
    return () => { active = false; };
  }, [hotelRef]);

  useEffect(() => {
    if (validation) return;
    let active = true;
    void hotelService.getHotelRooms(hotelRef, search).then((roomData) => { if (active) setAvailability(roomData); }).catch(() => { if (active) setAvailabilityError("Live room availability could not be checked. Your dates and guest selection have not changed."); });
    return () => { active = false; };
  }, [hotelRef, search, validation]);

  if (error) return <div className="container-shell py-14"><StatePanel title="Hotel unavailable" message={error} /></div>;
  if (!hotel) return <HotelDetailSkeleton />;

  const mode = availability?.booking_mode ?? hotel.booking_mode;
  return (
    <div>
      <header className="border-b border-[var(--line)] bg-white">
        <div className="container-shell py-8">
          <Link href={`/hotels?${hotelSearchQuery(search)}`} className="text-sm font-black text-[var(--accent)] hover:text-[var(--accent-strong)]">← Back to stays</Link>
          <div className="mt-7 flex flex-wrap items-start justify-between gap-5">
            <div><p className="eyebrow">{propertyLabel(hotel.property_type)}</p><h1 className="page-title mt-3">{hotel.name}</h1><p className="mt-3 max-w-2xl text-slate-500">{hotel.address_line1}{hotel.address_line2 ? `, ${hotel.address_line2}` : ""}, {hotel.city}, {hotel.state} {hotel.postal_code}</p></div>
            <div className="flex flex-wrap gap-2">{Number(hotel.star_rating) > 0 && <span className="status-pill bg-[var(--surface-muted)] text-slate-700" aria-label={`${hotel.star_rating} star property classification`}>{hotel.star_rating} ★ property</span>}<ModePill mode={mode} /></div>
          </div>
        </div>
      </header>

      <main className="container-shell py-8 sm:py-12">
        <Gallery hotel={hotel} />
        <nav aria-label="Hotel page sections" className="mt-6 flex gap-2 overflow-x-auto border-b border-[var(--line)] pb-3 text-sm font-bold text-slate-600"><a href="#overview" className="rounded-lg px-3 py-2 hover:bg-white hover:text-[var(--accent)]">Overview</a><a href="#rooms" className="rounded-lg px-3 py-2 hover:bg-white hover:text-[var(--accent)]">Rooms</a>{hotel.amenities.length > 0 && <a href="#facilities" className="rounded-lg px-3 py-2 hover:bg-white hover:text-[var(--accent)]">Facilities</a>}{hotel.policy && <a href="#policies" className="rounded-lg px-3 py-2 hover:bg-white hover:text-[var(--accent)]">Policies</a>}<a href="#reviews" className="rounded-lg px-3 py-2 hover:bg-white hover:text-[var(--accent)]">Reviews</a><a href="#location" className="rounded-lg px-3 py-2 hover:bg-white hover:text-[var(--accent)]">Location</a></nav>

        <div className="mt-8 grid items-start gap-7 lg:grid-cols-[1.55fr_.75fr]">
          <div className="space-y-7">
            <section id="overview" className="content-card scroll-mt-28"><p className="eyebrow">Overview</p><h2 className="mt-3 text-2xl font-black tracking-tight text-[var(--brand-strong)]">About this stay</h2>{hotel.description ? <p className="mt-4 whitespace-pre-wrap leading-7 text-slate-600">{hotel.description}</p> : <p className="mt-4 text-sm leading-6 text-slate-500">A property description has not been published.</p>}</section>
            {hotel.amenities.length > 0 && <section id="facilities" className="content-card scroll-mt-28"><p className="eyebrow">Facilities</p><h2 className="mt-3 text-2xl font-black tracking-tight text-[var(--brand-strong)]">Property amenities</h2><div className="mt-6 flex flex-wrap gap-2">{hotel.amenities.map((amenity) => <span className="amenity-chip" key={amenity.id}>{amenity.name}</span>)}</div></section>}
            {hotel.policy && <PolicyCard policy={hotel.policy} />}
          </div>
          <aside className="content-card lg:sticky lg:top-24"><p className="eyebrow">Stay details</p><h2 className="mt-3 text-xl font-black text-[var(--brand-strong)]">At a glance</h2><dl className="mt-6 divide-y divide-slate-100 text-sm"><Row label="Check-in" value={hotel.check_in_time.slice(0, 5)} /><Row label="Check-out" value={hotel.check_out_time.slice(0, 5)} /><Row label="Travel dates" value={search.checkIn && search.checkOut ? `${search.checkIn} — ${search.checkOut}` : "Not selected"} /><Row label="Guests" value={`${search.adults} adults, ${search.children} children`} /><Row label="Rooms" value={String(search.rooms)} /></dl><a href="#rooms" className="primary-button mt-6 w-full">Check rooms</a></aside>
        </div>

        <section id="rooms" className="mt-14 scroll-mt-24" aria-labelledby="rooms-heading">
          <p className="eyebrow">Live availability</p><h2 id="rooms-heading" className="section-title mt-3">Choose your room</h2><p className="mt-3 max-w-2xl text-slate-500">Select dates and guests to request live inventory and pricing from Maharashtra Tourist Places.</p>
          <div className="mt-7"><StayDateForm hotelSlug={hotel.slug} search={search} /></div>
          <BookingModeNotice mode={mode} />
          {validation ? <div className="mt-7"><StatePanel title="Select travel dates" message={validation} /></div> : availabilityError ? <div className="mt-7"><StatePanel title="Availability unavailable" message={availabilityError} /></div> : !availability ? <RoomsSkeleton /> : availability.items.length === 0 ? <div className="mt-7"><StatePanel title="No rooms available" message="No customer-bookable room has sufficient inventory for this date and guest selection. Try different dates, fewer rooms, or another guest count." /></div> : <div className="mt-7 space-y-5" aria-live="polite">{availability.items.map((room) => <RoomCard key={room.id} hotel={hotel} room={room} search={search} mode={availability.booking_mode} />)}</div>}
        </section>

        <ReviewSection reviews={reviews} />
        <section id="location" className="content-card mt-12 scroll-mt-28"><p className="eyebrow">Location</p><h2 className="mt-3 text-2xl font-black text-[var(--brand-strong)]">{hotel.city}, {hotel.state}</h2><address className="mt-4 not-italic leading-7 text-slate-600">{hotel.address_line1}{hotel.address_line2 && <><br />{hotel.address_line2}</>}<br />{hotel.city}{hotel.district && hotel.district !== hotel.city ? `, ${hotel.district}` : ""}, {hotel.state} {hotel.postal_code}<br />{hotel.country}</address></section>
      </main>
    </div>
  );
}

function StayDateForm({ hotelSlug, search }: { hotelSlug: string; search: HotelSearchParams }) {
  const router = useRouter();
  const [error, setError] = useState("");
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const next = { ...search, checkIn: String(form.get("checkIn") ?? ""), checkOut: String(form.get("checkOut") ?? ""), adults: Number(form.get("adults")), children: Number(form.get("children")), rooms: Number(form.get("rooms")) };
    const validation = validateStaySelection(next);
    if (validation) return setError(validation);
    setError("");
    router.push(`/hotels/${hotelSlug}?${hotelSearchQuery(next)}#rooms`);
  }
  return <form onSubmit={submit} className="rounded-2xl border border-[var(--line)] bg-white p-4 shadow-[var(--shadow-sm)]" noValidate><div className="grid items-end gap-3 sm:grid-cols-2 lg:grid-cols-[1fr_1fr_.7fr_.7fr_.7fr_auto]"><Field label="Check-in"><input name="checkIn" aria-label="Check-in" type="date" defaultValue={search.checkIn} className="field-input" required /></Field><Field label="Check-out"><input name="checkOut" aria-label="Check-out" type="date" defaultValue={search.checkOut} className="field-input" required /></Field><Field label="Adults"><input name="adults" aria-label="Adults" type="number" min={1} max={20} defaultValue={search.adults} className="field-input" /></Field><Field label="Children"><input name="children" aria-label="Children" type="number" min={0} max={20} defaultValue={search.children} className="field-input" /></Field><Field label="Rooms"><input name="rooms" aria-label="Rooms" type="number" min={1} max={10} defaultValue={search.rooms} className="field-input" /></Field><button type="submit" className="primary-button min-h-[3.15rem]">Check availability</button></div>{error && <p role="alert" className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm font-semibold text-[var(--danger)]">{error}</p>}</form>;
}

function Field({ label, children }: { label: string; children: React.ReactNode }) { return <label><span className="field-label">{label}</span>{children}</label>; }

function Gallery({ hotel }: { hotel: HotelDetail }) {
  const images = hotel.images.slice(0, 5);
  if (!images.length) return <div className="destination-image-fallback grid min-h-[360px] place-items-center rounded-2xl border border-[var(--line)]"><div className="text-center"><p className="text-xs font-black tracking-[.18em] text-slate-500">MAHARASHTRA TOURIST PLACES STAY</p><p className="mt-3 text-xl font-black text-[var(--brand-strong)]">Property photos unavailable</p></div></div>;
  return <section aria-label={`${hotel.name} photo gallery`} className="grid h-[360px] gap-2 overflow-hidden rounded-2xl sm:h-[460px] md:grid-cols-4 md:grid-rows-2">{images.map((image, index) => <figure key={image.id} className={`relative overflow-hidden bg-slate-100 ${index === 0 ? "md:col-span-2 md:row-span-2" : ""}`}><MediaImage src={image.image_url} alt={image.alt_text || `${hotel.name} property view ${index + 1}`} eager={index === 0} className="absolute inset-0 h-full w-full object-cover" fallback={<div className="destination-image-fallback absolute inset-0 grid place-items-center text-xs font-bold text-slate-500">Photo unavailable</div>} /></figure>)}</section>;
}

function RoomCard({ hotel, room, search, mode }: { hotel: HotelDetail; room: RoomAvailability; search: HotelSearchParams; mode: BookingGatewayStatus }) {
  const image = room.images[0];
  const action = mode === "ACTIVE" ? "Book this room" : mode === "BOOKING_ON_REQUEST" ? "Request this room" : "Booking unavailable";
  const href = `/booking/review?hotelId=${hotel.id}&roomId=${room.id}&${hotelSearchQuery(search)}`;
  return <article className="grid overflow-hidden rounded-2xl border border-[var(--line)] bg-white shadow-[var(--shadow-sm)] md:grid-cols-[220px_minmax(0,1fr)_220px]"><div className="relative min-h-52 bg-[var(--surface-muted)]"><MediaImage src={image?.image_url} alt={image?.alt_text || `${room.name} at ${hotel.name}`} className="absolute inset-0 h-full w-full object-cover" fallback={<div className="destination-image-fallback absolute inset-0 grid place-items-center text-xs font-bold text-slate-500">Room photo unavailable</div>} /></div><div className="p-5 sm:p-6"><span className="status-pill bg-emerald-50 text-[var(--success)]">Available for this stay</span><h3 className="mt-3 text-2xl font-black tracking-tight text-[var(--brand-strong)]">{room.name}</h3>{room.description && <p className="mt-2 text-sm leading-6 text-slate-500">{room.description}</p>}<div className="mt-4 flex flex-wrap gap-x-5 gap-y-2 text-sm font-semibold text-slate-600"><span>{room.bed_count} × {room.bed_type}</span><span>Up to {room.max_guests} guests</span>{room.room_size_sqm && <span>{room.room_size_sqm} m²</span>}</div>{hotel.policy?.cancellation_policy && <p className="mt-4 text-xs leading-5 text-slate-500">Cancellation: {hotel.policy.cancellation_policy}</p>}</div><div className="flex flex-col items-start justify-center border-t border-[var(--line)] p-5 md:items-end md:border-l md:border-t-0"><p className="text-[11px] font-bold uppercase tracking-wide text-slate-400">Average per night</p><p className="mt-1 text-2xl font-black tracking-tight text-[var(--brand-strong)]">{formatMoney(room.price_per_night, room.currency)}</p><p className="mt-3 text-sm font-bold text-slate-700">{formatMoney(room.estimated_total, room.currency)} room total</p><p className="mt-1 text-xs text-slate-400">Taxes and fees shown after backend quote</p>{mode === "PAUSED" ? <span className="mt-5 w-full rounded-xl bg-slate-100 px-4 py-3 text-center text-sm font-black text-slate-600">{action}</span> : <Link href={href} className={`${mode === "ACTIVE" ? "primary-button" : "secondary-button"} mt-5 w-full`}>{action}</Link>}</div></article>;
}

function BookingModeNotice({ mode }: { mode: BookingGatewayStatus }) {
  if (mode === "ACTIVE") return <p className="mt-5 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm leading-6 text-emerald-800"><strong>Instant booking:</strong> selecting a room continues to traveller details, a fresh backend quote, an inventory hold, and payment.</p>;
  if (mode === "BOOKING_ON_REQUEST") return <p className="mt-5 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm leading-6 text-amber-900"><strong>Booking on request:</strong> the property must accept the request before payment becomes available. Selecting a room does not confirm the stay.</p>;
  return <p className="mt-5 rounded-xl border border-slate-200 bg-slate-100 p-4 text-sm leading-6 text-slate-700"><strong>Booking currently unavailable:</strong> room selection is disabled until the property resumes bookings.</p>;
}

function ModePill({ mode }: { mode: BookingGatewayStatus }) {
  const style = mode === "ACTIVE" ? "bg-emerald-50 text-emerald-700" : mode === "BOOKING_ON_REQUEST" ? "bg-amber-50 text-amber-800" : "bg-slate-100 text-slate-600";
  const label = mode === "ACTIVE" ? "Instant booking" : mode === "BOOKING_ON_REQUEST" ? "Booking on request" : "Booking unavailable";
  return <span className={`status-pill ${style}`}>{label}</span>;
}

function PolicyCard({ policy }: { policy: HotelDetail["policy"] }) {
  if (!policy) return null;
  const items = Object.entries(policy).filter(([, value]) => value);
  if (!items.length) return null;
  return <section id="policies" className="content-card scroll-mt-28"><p className="eyebrow">Before you arrive</p><h2 className="mt-3 text-2xl font-black tracking-tight text-[var(--brand-strong)]">Property policies</h2><dl className="mt-6 grid gap-5 sm:grid-cols-2">{items.map(([key, value]) => <div key={key}><dt className="text-sm font-black capitalize text-slate-800">{key.replaceAll("_", " ")}</dt><dd className="mt-1.5 text-sm leading-6 text-slate-500">{value}</dd></div>)}</dl></section>;
}

function ReviewSection({ reviews }: { reviews: PublicReviewList | null }) {
  if (!reviews?.items.length) return <section id="reviews" className="content-card mt-12 scroll-mt-28"><p className="eyebrow">Verified stays</p><h2 className="mt-3 text-2xl font-black text-[var(--brand-strong)]">No published verified-stay reviews yet</h2></section>;
  return <section id="reviews" className="mt-12 scroll-mt-28"><div className="flex flex-wrap items-end justify-between gap-4"><div><p className="eyebrow">Verified stays</p><h2 className="section-title mt-3">Guest reviews</h2></div>{reviews.average_overall_rating !== null && <div className="text-right"><strong className="text-2xl text-[var(--brand-strong)]">{reviews.average_overall_rating} / 5</strong><p className="text-xs text-slate-500">Across {reviews.total} published review{reviews.total === 1 ? "" : "s"}</p></div>}</div><div className="mt-6 grid gap-4 lg:grid-cols-2">{reviews.items.map((review) => <article key={review.id} className="content-card"><div className="flex justify-between gap-3"><span className="status-pill bg-emerald-50 text-emerald-700">✓ Verified stay</span><strong aria-label={`${review.overall_rating} out of 5`}>{review.overall_rating} / 5</strong></div><p className="mt-4 whitespace-pre-wrap leading-7 text-slate-600">{review.review_text}</p><p className="mt-4 text-xs font-bold text-slate-400">{review.reviewer_label}</p>{review.hotel_response && <div className="mt-5 rounded-xl bg-[var(--surface-muted)] p-4 text-sm"><strong>Response from the property</strong><p className="mt-2 text-slate-600">{review.hotel_response.response_text}</p></div>}</article>)}</div></section>;
}

function RoomsSkeleton() { return <div className="mt-7 space-y-5" aria-label="Loading room availability">{[1, 2].map((item) => <div key={item} className="grid overflow-hidden rounded-2xl border border-[var(--line)] bg-white md:grid-cols-[220px_1fr]"><div className="skeleton min-h-52" /><div className="p-6"><div className="skeleton h-5 w-28 rounded" /><div className="skeleton mt-4 h-8 w-1/2 rounded" /><div className="skeleton mt-4 h-4 w-full rounded" /></div></div>)}</div>; }
function Row({ label, value }: { label: string; value: string }) { return <div className="flex justify-between gap-4 py-4 first:pt-0 last:pb-0"><dt className="text-slate-500">{label}</dt><dd className="text-right font-black text-slate-800">{value}</dd></div>; }
function HotelDetailSkeleton() { return <div className="container-shell py-12"><div className="skeleton h-4 w-32 rounded" /><div className="skeleton mt-5 h-14 w-2/3 rounded" /><div className="skeleton mt-8 h-[430px] rounded-2xl" /></div>; }
function propertyLabel(value: string) { return value.charAt(0) + value.slice(1).toLowerCase(); }
