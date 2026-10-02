import Link from "next/link";
import { SafariArtwork } from "@/src/components/safari/SafariArtwork";
import type { Safari } from "@/src/types/safari";

export function SafariCard({ safari }: { safari: Safari }) {
  const location = safari.destination_name || safari.district_name;
  return <article className="group relative overflow-hidden rounded-[1.5rem] bg-[#173326] shadow-[0_18px_50px_rgba(22,51,38,.14)] transition duration-300 hover:-translate-y-1 hover:shadow-[0_26px_65px_rgba(22,51,38,.22)] motion-reduce:transform-none motion-reduce:transition-none">
    <SafariArtwork safari={safari} alt={`${safari.name} — representative Maharashtra wildlife imagery`} />
    <div className="pointer-events-none absolute inset-0 bg-gradient-to-t from-[#07140e] via-[#07140e]/35 to-transparent" aria-hidden="true" />
    <div className="absolute inset-x-0 bottom-0 p-6 text-white sm:p-7"><span className="inline-flex rounded-full border border-white/25 bg-black/30 px-3 py-1 text-[10px] font-black uppercase tracking-[.16em] backdrop-blur-sm">Wildlife inspiration</span>{location && <p className="mt-5 text-xs font-black uppercase tracking-[.16em] text-[#e6b675]">{location}{safari.destination_name && safari.district_name ? ` · ${safari.district_name}` : ""}</p>}<h2 className="mt-2 font-serif text-3xl font-semibold tracking-tight">{safari.name}</h2><p className="mt-3 line-clamp-2 text-sm leading-6 text-white/75">{safari.short_description}</p><Link href={`/safaris/${safari.slug}`} className="mt-5 inline-flex min-h-11 items-center text-sm font-black text-white outline-offset-4 hover:text-[#f0bf80] focus-visible:outline-2 focus-visible:outline-white">Explore Safari <span aria-hidden className="ml-2 transition-transform group-hover:translate-x-1">→</span></Link></div>
  </article>;
}
