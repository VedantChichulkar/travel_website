import Link from "next/link";

import { MAHARASHTRA_DESTINATIONS } from "@/src/data/maharashtra-destinations";
import { MAHARASHTRA_EXPERIENCES } from "@/src/data/maharashtra-experiences";

export function DestinationCulture({ districtSlug }: { districtSlug: string }) {
  const content = MAHARASHTRA_DESTINATIONS.find((destination) => destination.districtSlug === districtSlug);
  if (!content) return null;

  const categories = MAHARASHTRA_EXPERIENCES.filter((category) => content.categories.includes(category.slug));
  return <section aria-labelledby={`culture-${districtSlug}`} className="mt-16"><p className="eyebrow">Experiences & culture</p><h2 id={`culture-${districtSlug}`} className="section-title mt-3">Explore around {content.city}</h2><p className="mt-4 max-w-3xl text-sm leading-6 text-slate-600">{content.descriptor}. Continue through Maharashtra Tourist Places’ curated themes or use these place references as a starting point for local planning.</p><div className="mt-6 flex flex-wrap gap-2">{categories.map((category) => <Link key={category.slug} href={`/experiences?category=${category.slug}&district=${districtSlug}#explore-experiences`} className="rounded-full border border-[var(--line)] bg-white px-4 py-2 text-sm font-bold text-[var(--accent-strong)] hover:border-slate-300">{category.title}</Link>)}</div><div className="mt-6 rounded-2xl border border-[var(--line)] bg-[var(--surface-muted)] p-6"><h3 className="text-sm font-black uppercase tracking-[.12em] text-[var(--brand)]">Curated place references</h3><ul className="mt-4 grid gap-3 text-sm text-slate-600 sm:grid-cols-3">{content.attractions.map((attraction) => <li key={attraction} className="rounded-xl border border-[var(--line)] bg-white px-4 py-3 font-semibold">{attraction}</li>)}</ul></div></section>;
}
