import Image from "next/image";
import Link from "next/link";

import { SectionHeading } from "@/src/components/SectionHeading";

export function CultureSection() {
  return (
    <section id="culture" className="overflow-hidden bg-[#f1e8dc] py-20">
      <div className="container-shell">
        <div className="grid gap-10 lg:grid-cols-[.9fr_1.1fr] lg:items-end">
          <div>
            <SectionHeading eyebrow="Culture & traditions" title="A living culture, carried forward" description="Maharashtra’s traditions are shaped by devotion, craft, performance, food, and distinct regional identities. Travel with curiosity and respect for the communities that sustain them." />
            <div className="relative mt-8 aspect-[4/3] overflow-hidden rounded-[1.6rem] shadow-[var(--shadow-lg)]">
              <Image src="/images/interests/culture-traditions.png" alt="Editorial illustration representing Maharashtra craft and cultural traditions" fill sizes="(min-width: 1024px) 42vw, 100vw" className="object-cover" />
              <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-slate-950/90 to-transparent px-6 pb-6 pt-20 text-white">
                <p className="text-xs font-black uppercase tracking-[.14em] text-[#ffc1a9]">Source-reviewed discovery</p>
                <p className="mt-2 text-sm leading-6 text-slate-200">Follow individual stories for verified cultural and regional context.</p>
              </div>
            </div>
          </div>
          <div className="grid gap-5">
            <article className="rounded-2xl border border-[#ddcdbd] bg-white/85 p-7 shadow-sm backdrop-blur"><p className="eyebrow">Stories & traditions</p><h3 className="mt-3 text-2xl font-black text-[var(--brand-strong)]">Culture with its context intact</h3><p className="mt-3 text-sm leading-7 text-slate-600">Explore Wari, Lavani, Warli art, Paithani weaving and Ganeshotsav as editorial stories—not fabricated geographic Places.</p><Link href="/explore/culture-traditions" className="mt-6 inline-flex text-sm font-black text-[var(--accent)]">Explore culture <span aria-hidden className="ml-1">→</span></Link></article>
            <article className="rounded-2xl border border-[#ddcdbd] bg-white/85 p-7 shadow-sm backdrop-blur"><p className="eyebrow">Regional flavours</p><h3 className="mt-3 text-2xl font-black text-[var(--brand-strong)]">Foodways beyond a menu</h3><p className="mt-3 text-sm leading-7 text-slate-600">Read about regional cuisines and festival tables without restaurant listings, rankings or invented origin claims.</p><Link href="/explore/food-local-flavours" className="mt-6 inline-flex text-sm font-black text-[var(--accent)]">Explore food stories <span aria-hidden className="ml-1">→</span></Link></article>
          </div>
        </div>
      </div>
    </section>
  );
}
