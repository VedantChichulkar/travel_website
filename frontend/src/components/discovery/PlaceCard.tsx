import Link from "next/link";

import { DiscoveryMediaImage } from "@/src/components/discovery/DiscoveryMediaImage";
import { resolvePlaceMedia } from "@/src/lib/discovery-media";
import type { PublicPlace } from "@/src/types/place";

export function PlaceCard({ place }: { place: PublicPlace }) {
  const media = resolvePlaceMedia(place);
  return (
    <article className="group flex h-full flex-col overflow-hidden rounded-2xl border border-[var(--line)] bg-white shadow-[var(--shadow-sm)]">
      <div className="relative h-52 overflow-hidden bg-[var(--surface-muted)]">
        <DiscoveryMediaImage media={media} className="transition duration-500 group-hover:scale-[1.025] motion-reduce:transition-none" />
      </div>
      <div className="flex flex-1 flex-col p-5 sm:p-6">
        <p className="text-[10px] font-black uppercase tracking-[.15em] text-[var(--accent)]">{place.destination?.name ?? `${place.district.name} district`}</p>
        <h3 className="mt-2 text-xl font-black tracking-tight text-[var(--brand)]">{place.name}</h3>
        {place.short_description && <p className="mt-3 line-clamp-3 text-sm leading-6 text-slate-600">{place.short_description}</p>}
        {place.interests.length > 0 && <div className="mt-4 flex flex-wrap gap-1.5">{place.interests.slice(0, 3).map((interest) => <span key={interest.slug} className="rounded-full bg-[var(--accent-soft)] px-2.5 py-1 text-[10px] font-bold text-[var(--accent-strong)]">{interest.name}</span>)}</div>}
        <Link href={place.path} className="mt-auto inline-flex pt-5 text-sm font-black text-[var(--accent)] hover:text-[var(--accent-strong)]">Explore place <span aria-hidden className="ml-1 transition-transform group-hover:translate-x-1">→</span></Link>
      </div>
    </article>
  );
}
