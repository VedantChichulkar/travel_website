import { DestinationImage } from "@/src/components/destinations/DestinationImage";
import type { PublicDiscoveryMedia, PublicFAQ } from "@/src/types/place";

export function DiscoveryGallery({ name, media }: { name: string; media: PublicDiscoveryMedia[] }) {
  if (!media.length) return null;
  return <section className="mt-20" aria-labelledby="gallery-title"><p className="eyebrow">Gallery</p><h2 id="gallery-title" className="section-title mt-3">See {name}</h2><div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">{media.map((item, index) => <figure key={item.id} className={`${index === 0 ? "sm:col-span-2" : ""} overflow-hidden rounded-2xl border border-[var(--line)] bg-white`}><div className="h-64 sm:h-72"><DestinationImage src={item.public_url} name={name} alt={item.alt_text} /></div>{item.attribution_text && <figcaption className="px-4 py-3 text-xs text-slate-500">{item.attribution_text}</figcaption>}</figure>)}</div></section>;
}

export function DiscoveryFAQs({ name, faqs }: { name: string; faqs: PublicFAQ[] }) {
  if (!faqs.length) return null;
  return <section className="mt-20 max-w-3xl" aria-labelledby="faq-title"><p className="eyebrow">Plan your visit</p><h2 id="faq-title" className="section-title mt-3">Frequently asked questions about {name}</h2><div className="mt-8 divide-y divide-[var(--line)] rounded-2xl border border-[var(--line)] bg-white px-5 sm:px-7">{faqs.map((faq) => <details key={faq.id} className="group py-5"><summary className="flex min-h-11 cursor-pointer list-none items-center justify-between gap-4 font-black text-[var(--brand)] focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[var(--accent)]">{faq.question}<span aria-hidden className="text-xl text-[var(--accent)] group-open:rotate-45 motion-reduce:transition-none">+</span></summary><p className="pb-2 pt-3 whitespace-pre-wrap text-sm leading-7 text-slate-600">{faq.answer}</p></details>)}</div></section>;
}
