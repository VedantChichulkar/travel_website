"use client";

import { useEffect, useState } from "react";

import { HotelCard } from "@/src/components/HotelCard";
import { hotelService } from "@/src/services/hotel.service";
import type { HotelSearchResponse } from "@/src/types/hotel";

const blankSearch = { city: "", checkIn: "", checkOut: "", adults: 2, children: 0, rooms: 1, amenities: [], sort: "recommended" as const };
export function FeaturedHotels() {
  const [result, setResult] = useState<HotelSearchResponse | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => { let active = true; void hotelService.getFeaturedHotels().then((data) => { if (active) setResult(data); }).catch(() => { if (active) setFailed(true); }); return () => { active = false; }; }, []);
  const hotels = (result?.items ?? []).filter((hotel) => hotel.is_featured && hotel.state.toLocaleLowerCase("en-IN") === "maharashtra");
  if (failed || (result && hotels.length === 0)) return <div className="surface-card p-8 text-center"><p className="font-bold text-[var(--brand)]">No stays are available to feature right now.</p><p className="mt-2 text-sm text-slate-500">Use the search above to check the live hotel catalogue.</p></div>;
  if (!result) return <div className="grid gap-5 lg:grid-cols-3">{[1, 2, 3].map((item) => <div key={item} className="skeleton h-96 rounded-[1.35rem]" />)}</div>;
  return <div className="grid gap-5 lg:grid-cols-3">{hotels.slice(0, 3).map((hotel) => <HotelCard key={hotel.id} hotel={hotel} search={{ ...blankSearch, city: hotel.city }} variant="compact" />)}</div>;
}
