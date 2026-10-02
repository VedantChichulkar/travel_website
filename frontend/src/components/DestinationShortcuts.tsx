"use client";

import Image from "next/image";
import { useRouter } from "next/navigation";

import { MAHARASHTRA_DESTINATIONS } from "@/src/data/maharashtra-destinations";
import { hotelSearchQuery } from "@/src/lib/hotel-search";

function iso(date: Date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}

export function DestinationShortcuts() {
  const router = useRouter();

  function explore(city: string) {
    const checkIn = new Date();
    checkIn.setDate(checkIn.getDate() + 30);
    const checkOut = new Date(checkIn);
    checkOut.setDate(checkOut.getDate() + 3);
    router.push(`/hotels?${hotelSearchQuery({ city, checkIn: iso(checkIn), checkOut: iso(checkOut), adults: 2, children: 0, rooms: 1, amenities: [], sort: "recommended" })}`);
  }

  return (
    <div className="grid auto-rows-fr gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
      {MAHARASHTRA_DESTINATIONS.map((destination) => (
        <button
          key={destination.city}
          type="button"
          onClick={() => explore(destination.city)}
          className="group flex h-full min-h-[31rem] flex-col overflow-hidden rounded-[1.4rem] border border-slate-200 bg-white text-left shadow-sm outline-none transition duration-300 hover:-translate-y-1 hover:border-slate-300 hover:shadow-xl focus-visible:ring-4 focus-visible:ring-[var(--accent)]/35"
          aria-label={`Explore stays near ${destination.city}`}
        >
          <span className="relative block h-52 w-full shrink-0 overflow-hidden bg-slate-100">
            <Image
              src={destination.image}
              alt={destination.imageAlt}
              fill
              sizes="(min-width: 1280px) 20vw, (min-width: 1024px) 33vw, (min-width: 640px) 50vw, 100vw"
              className="object-cover transition duration-500 ease-out group-hover:scale-[1.035]"
            />
          </span>
          <span className="flex flex-1 flex-col p-5">
            <span className="text-[10px] font-black uppercase tracking-[.14em] text-[var(--accent-strong)]">{destination.experience}</span>
            <span className="mt-2 text-[11px] font-bold uppercase tracking-[.1em] text-slate-400">{destination.code} · {destination.region}</span>
            <strong className="mt-3 block text-[1.35rem] font-black leading-[1.08] tracking-[-.025em] text-[var(--brand-strong)]">{destination.city}</strong>
            <span className="mt-3 block text-sm leading-6 text-slate-600">{destination.descriptor}</span>
            <span className="mt-4 block border-t border-slate-100 pt-4 text-xs font-semibold leading-5 text-slate-500">{destination.attractions.slice(0, 2).join(" · ")}</span>
            <span className="mt-auto pt-5 text-xs font-black text-[var(--brand)]">Explore stays <span aria-hidden className="inline-block transition-transform group-hover:translate-x-1">→</span></span>
          </span>
        </button>
      ))}
    </div>
  );
}
