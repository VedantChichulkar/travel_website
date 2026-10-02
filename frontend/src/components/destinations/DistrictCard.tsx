import Link from "next/link";

import { DestinationImage } from "@/src/components/destinations/DestinationImage";
import { curatedDestinationForDistrict } from "@/src/data/maharashtra-destinations";
import type { PublicDistrict } from "@/src/types/destination";

export function DistrictCard({ district }: { district: PublicDistrict }) {
  const image = district.hero_image_url || curatedDestinationForDistrict(district.slug)?.image || null;
  return (
    <article className="group flex h-full flex-col overflow-hidden rounded-2xl border border-[var(--line)] bg-white shadow-[var(--shadow-sm)] transition hover:border-slate-300">
      <div className="h-44 overflow-hidden bg-[var(--surface-muted)]"><DestinationImage src={image} name={`${district.name} district`} className="transition duration-500 group-hover:scale-[1.025]" /></div>
      <div className="flex flex-1 flex-col p-5">
        <p className="text-[10px] font-black uppercase tracking-[.15em] text-[var(--accent)]">{district.division} division</p>
        <h2 className="mt-2 text-xl font-black tracking-tight text-[var(--brand)]">{district.name}</h2>
        {district.short_description && <p className="mt-3 line-clamp-3 text-sm leading-6 text-slate-600">{district.short_description}</p>}
        <Link href={district.path} className="mt-auto inline-flex pt-5 text-sm font-black text-[var(--accent)] hover:text-[var(--accent-strong)]">Explore district <span aria-hidden className="ml-1 transition-transform group-hover:translate-x-1">→</span></Link>
      </div>
    </article>
  );
}
