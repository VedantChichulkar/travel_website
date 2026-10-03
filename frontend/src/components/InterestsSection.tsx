import Link from "next/link";

import { SectionHeading } from "@/src/components/SectionHeading";
import { KNOWN_INTEREST_SLUGS, interestVisual } from "@/src/data/place-interests";

export function InterestsSection() {
  return (
    <section id="explore-by-interest" className="bg-white py-20">
      <div className="container-shell">
        <SectionHeading eyebrow="Ways to explore" title="Follow what draws you in" description="Nine interests to help shape a Maharashtra journey. Discover places, culture, and food through the existing interest guides." />
        <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {KNOWN_INTEREST_SLUGS.map((slug) => {
            const interest = interestVisual(slug)!;
            return (
              <Link href={`/explore/${slug}`} key={slug} className="group rounded-2xl border border-[var(--line)] bg-white p-6 shadow-[var(--shadow-sm)] transition hover:border-slate-300">
                <span className="grid h-11 w-11 place-items-center rounded-xl bg-[var(--accent-soft)] text-[11px] font-black tracking-wider text-[var(--accent-strong)]" aria-hidden>{interest.shortTitle.split(" ").filter((word) => word !== "&").slice(0, 2).map((word) => word[0]).join("")}</span>
                <h3 className="mt-6 text-xl font-black tracking-tight text-[var(--brand)]">{interest.shortTitle}</h3>
                <p className="mt-3 text-sm leading-6 text-slate-600">{interest.description}</p>
                <span className="mt-5 inline-flex text-sm font-black text-[var(--accent)]">Explore interest <span aria-hidden className="ml-1 transition-transform group-hover:translate-x-1">→</span></span>
              </Link>
            );
          })}
        </div>
      </div>
    </section>
  );
}
