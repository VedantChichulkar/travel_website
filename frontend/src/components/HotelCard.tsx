import Link from "next/link";

import { MediaImage } from "@/src/components/MediaImage";
import { formatMoney } from "@/src/lib/hotel-search";
import type { Hotel, HotelSearchParams } from "@/src/types/hotel";

function propertyLabel(value: string): string {
  return value[0] + value.slice(1).toLowerCase();
}

export function HotelCard({ hotel, search, variant = "wide" }: { hotel: Hotel; search: HotelSearchParams; variant?: "wide" | "compact" }) {
  const query = new URLSearchParams({ city: search.city, checkIn: search.checkIn, checkOut: search.checkOut, adults: String(search.adults), children: String(search.children), rooms: String(search.rooms) });
  if (search.destination) query.set("destination", search.destination);
  const href = `/hotels/${hotel.slug}?${query.toString()}`;
  const stars = Math.max(0, Math.min(5, Math.round(Number(hotel.star_rating))));
  const compact = variant === "compact";
  const dated = Boolean(search.checkIn && search.checkOut);
  const modeLabel = hotel.booking_mode === "ACTIVE" ? "Instant booking" : hotel.booking_mode === "BOOKING_ON_REQUEST" ? "Booking on request" : "Booking unavailable";

  return (
    <Link href={href} aria-label={`View ${hotel.name}`} className={`group grid overflow-hidden rounded-2xl border border-[var(--line)] bg-white shadow-[var(--shadow-sm)] outline-none transition duration-200 hover:border-slate-300 hover:shadow-[0_6px_18px_rgb(16_24_40/_.08)] focus-visible:ring-4 focus-visible:ring-[var(--accent)]/25 ${compact ? "grid-rows-[13rem_1fr]" : "md:grid-cols-[220px_minmax(0,1fr)] xl:grid-cols-[230px_minmax(0,1fr)_190px]"}`}>
      <div className={`relative overflow-hidden bg-[#e8edf1] ${compact ? "h-52" : "min-h-56"}`}>
        <MediaImage src={hotel.cover_image_url} alt={`${hotel.name} property view`} className="absolute inset-0 h-full w-full object-cover transition duration-500 group-hover:scale-[1.025]" fallback={<HotelImageFallback />} />
      </div>
      <div className="min-w-0 p-5 sm:p-6">
        <p className="text-xs font-black uppercase tracking-[.14em] text-[var(--accent-strong)]">{propertyLabel(hotel.property_type)}</p>
        <h2 className="mt-2 text-2xl font-black leading-tight tracking-[-.035em] text-[var(--brand-strong)]">{hotel.name}</h2>
        <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1"><p className="text-sm font-semibold text-slate-500">{hotel.city}{hotel.district && hotel.district !== hotel.city ? `, ${hotel.district}` : ""}, {hotel.state}</p>{stars > 0 && <span aria-label={`${hotel.star_rating} star property classification`} className="text-xs font-black tracking-wide text-slate-500">{"★".repeat(stars)}<span className="sr-only"> {hotel.star_rating} star property classification</span></span>}</div>
        {search.checkIn && search.checkOut && hotel.is_available && <p className="mt-4 flex items-center gap-2 text-xs font-extrabold text-[var(--success)]"><span className="h-2 w-2 rounded-full bg-emerald-600" />Available for your dates</p>}
        <p className={`mt-3 text-xs font-extrabold ${hotel.booking_mode === "ACTIVE" ? "text-emerald-700" : hotel.booking_mode === "BOOKING_ON_REQUEST" ? "text-amber-700" : "text-slate-500"}`}>{modeLabel}</p>
        {hotel.amenities.length > 0 && <div className="mt-4 flex flex-wrap gap-2">{hotel.amenities.slice(0, 4).map((amenity) => <span key={amenity.id} className="amenity-chip">{amenity.name}</span>)}</div>}
      </div>
      <div className={`flex border-slate-100 p-5 sm:p-6 ${compact ? "items-end justify-between gap-4 border-t" : "items-center justify-between gap-5 border-t md:col-span-2 xl:col-span-1 xl:flex-col xl:items-stretch xl:justify-center xl:border-l xl:border-t-0"}`}>
        <div><p className="text-[11px] font-bold uppercase tracking-wide text-slate-400">{dated ? "Average nightly rate" : "Base rate from"}</p><p className="mt-1 text-2xl font-black tracking-tight text-[var(--brand-strong)]">{hotel.starting_price && hotel.currency ? formatMoney(hotel.starting_price, hotel.currency) : "Check price"}</p><p className="mt-0.5 text-xs text-slate-400">{dated ? "for selected dates" : "dates required for availability"}</p></div>
        <span className={`primary-button pointer-events-none ${compact ? "!min-h-11" : "xl:mt-5 xl:w-full"}`}>View hotel <span aria-hidden>→</span></span>
      </div>
    </Link>
  );
}

function HotelImageFallback() {
  return <div className="destination-image-fallback absolute inset-0 grid place-items-center"><div className="text-center"><span className="text-[10px] font-black tracking-[.18em] text-slate-500">MAHARASHTRA TOURIST PLACES STAY</span><p className="mt-2 text-xs font-bold text-slate-500">Property photo unavailable</p></div></div>;
}
