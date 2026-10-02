import Image from "next/image";
import Link from "next/link";

import { interestVisual } from "@/src/data/place-interests";
import type { PublicInterest } from "@/src/types/place";

export function InterestCard({ interest, featured = false, preload = false }: { interest: PublicInterest; featured?: boolean; preload?: boolean }) {
  const visual = interestVisual(interest.slug);
  return (
    <Link href={interest.path} className={`group relative isolate flex min-h-72 overflow-hidden rounded-[1.35rem] bg-[var(--brand)] text-white shadow-[var(--shadow-sm)] ${featured ? "md:min-h-[31rem]" : "md:min-h-80"}`}>
      {visual && <Image src={visual.image} alt={visual.imageAlt} fill unoptimized preload={preload} sizes={featured ? "(max-width: 768px) 100vw, 58vw" : "(max-width: 768px) 100vw, 34vw"} className="object-cover transition duration-700 group-hover:scale-[1.035] motion-reduce:transition-none" style={{ objectPosition: visual.objectPosition }} />}
      <span className="absolute inset-0 bg-gradient-to-t from-[#061522]/95 via-[#061522]/35 to-black/10" aria-hidden />
      <span className="relative mt-auto flex w-full items-end justify-between gap-5 p-6 sm:p-7">
        <span>
          <span className="block text-[10px] font-black uppercase tracking-[.18em] text-[#c9e1f5]">{visual?.eyebrow ?? "Explore Maharashtra"}</span>
          <span className={`mt-2 block font-black tracking-[-.035em] ${featured ? "text-3xl sm:text-4xl" : "text-2xl"}`}>{visual?.shortTitle ?? interest.name}</span>
          {visual?.description && <span className="mt-3 hidden max-w-xl text-sm leading-6 text-white/75 sm:block">{visual.description}</span>}
        </span>
        <span className="grid h-11 w-11 shrink-0 place-items-center rounded-full border border-white/35 bg-white/10 text-lg backdrop-blur transition group-hover:translate-x-1 group-hover:bg-white group-hover:text-[var(--brand)]" aria-hidden>→</span>
      </span>
    </Link>
  );
}
