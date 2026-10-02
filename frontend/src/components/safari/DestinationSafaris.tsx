"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { safariService } from "@/src/services/safari.service";
import type { Safari } from "@/src/types/safari";

export function DestinationSafaris({ districtSlug, destinationSlug, heading }: { districtSlug: string; destinationSlug?: string; heading: string }) {
  const [items, setItems] = useState<Safari[]>([]);
  useEffect(() => { void safariService.list().then((all) => setItems(all.filter((item) => destinationSlug ? item.district_slug === districtSlug && item.destination_slug === destinationSlug : item.district_slug === districtSlug))).catch(() => setItems([])); }, [destinationSlug, districtSlug]);
  if (!items.length) return null;
  return <section aria-labelledby={`safaris-${districtSlug}-${destinationSlug || "district"}`} className="mt-16"><p className="eyebrow">Wildlife journeys</p><h2 id={`safaris-${districtSlug}-${destinationSlug || "district"}`} className="section-title mt-3">{heading}</h2><p className="mt-4 max-w-2xl text-sm leading-6 text-slate-600">These safaris are linked to this destination by Maharashtra Tourist Places’ catalogue. Availability is checked after you send a request.</p><div className="mt-7 grid gap-4 md:grid-cols-2">{items.map((item) => <article key={item.id} className="rounded-2xl border border-[var(--line)] bg-white p-6 shadow-[var(--shadow-sm)]"><p className="text-xs font-black uppercase tracking-[.14em] text-[var(--accent-strong)]">Managed safari request</p><h3 className="mt-2 text-xl font-black text-[var(--brand)]">{item.name}</h3><p className="mt-3 line-clamp-2 text-sm leading-6 text-slate-600">{item.short_description}</p><Link href={`/safaris/${item.slug}`} className="mt-5 inline-flex text-sm font-black text-[var(--accent)] hover:text-[var(--accent-strong)]">Explore safari <span aria-hidden className="ml-1">→</span></Link></article>)}</div></section>;
}
