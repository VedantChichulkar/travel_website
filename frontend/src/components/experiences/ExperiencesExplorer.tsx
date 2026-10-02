"use client";

import Image from "next/image";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { DestinationImage } from "@/src/components/destinations/DestinationImage";
import { SafariTeaser } from "@/src/components/SafariTeaser";
import { MAHARASHTRA_DESTINATIONS } from "@/src/data/maharashtra-destinations";
import { isExperienceCategory, MAHARASHTRA_EXPERIENCES } from "@/src/data/maharashtra-experiences";
import { destinationService } from "@/src/services/destination.service";
import type { PublicDistrict } from "@/src/types/destination";

export function ExperiencesExplorer() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const categoryParam = searchParams.get("category");
  const districtParam = searchParams.get("district") ?? "";
  const activeCategory = isExperienceCategory(categoryParam) ? categoryParam : null;
  const [districts, setDistricts] = useState<PublicDistrict[] | null>(null);
  const [directoryFailed, setDirectoryFailed] = useState(false);

  useEffect(() => {
    let active = true;
    void destinationService.listDistricts().then((response) => {
      if (active) setDistricts(response.items);
    }).catch(() => {
      if (active) setDirectoryFailed(true);
    });
    return () => { active = false; };
  }, []);

  const districtBySlug = useMemo(() => new Map((districts ?? []).map((district) => [district.slug, district])), [districts]);
  const visible = MAHARASHTRA_DESTINATIONS.filter((destination) => {
    const categoryMatches = !activeCategory || destination.categories.includes(activeCategory);
    return categoryMatches && (!districtParam || destination.districtSlug === districtParam);
  });

  function setDistrict(value: string) {
    const params = new URLSearchParams(searchParams.toString());
    if (value) params.set("district", value); else params.delete("district");
    router.replace(`/experiences${params.size ? `?${params.toString()}` : ""}#explore-experiences`, { scroll: false });
  }

  return (
    <>
      <header className="border-b border-[var(--line)] bg-white">
        <div className="container-shell grid gap-9 py-12 lg:grid-cols-[.9fr_1.1fr] lg:items-center lg:py-16">
          <div>
            <p className="eyebrow">Experience Maharashtra</p>
            <h1 className="page-title mt-3 text-balance">Travel through place, food, nature, and living culture.</h1>
            <p className="body-lead mt-5 max-w-2xl">A curated starting point for exploring Maharashtra. Follow each story to its canonical destination, then use Maharashtra Tourist Places’ existing hotel or safari flow when you are ready to plan.</p>
            <div className="mt-7 flex flex-wrap gap-3"><Link href="#explore-experiences" className="primary-button">Browse themes</Link><Link href="/destinations" className="secondary-button">Explore destinations</Link></div>
          </div>
          <div className="relative aspect-[16/10] overflow-hidden rounded-2xl border border-[var(--line)] bg-[var(--surface-muted)] shadow-[var(--shadow-sm)]">
            <Image src="/images/maharashtra-hero.png" alt="A view across Maharashtra's varied landscape" fill priority sizes="(min-width: 1024px) 55vw, 100vw" className="object-cover" />
          </div>
        </div>
      </header>

      <main>
        <section id="explore-experiences" className="scroll-mt-20 border-b border-[var(--line)] bg-white py-16 sm:py-20" aria-labelledby="explore-heading">
          <div className="container-shell">
            <div className="flex flex-col justify-between gap-6 lg:flex-row lg:items-end"><div className="max-w-2xl"><p className="eyebrow">Explore experiences</p><h2 id="explore-heading" className="section-title mt-3">Destination-led travel ideas</h2><p className="body-lead mt-4">Every card leads to a canonical district page. Configured district imagery is preferred when the live directory is available; Maharashtra Tourist Places’ curated image is the fallback.</p></div><label className="w-full sm:w-72"><span className="field-label">Filter by destination</span><select className="field-input" value={districtParam} onChange={(event) => setDistrict(event.target.value)}><option value="">All featured destinations</option>{MAHARASHTRA_DESTINATIONS.map((destination) => <option key={destination.districtSlug} value={destination.districtSlug}>{destination.city}</option>)}</select></label></div>
            <nav aria-label="Experience category filter" className="mt-8 flex flex-wrap gap-2"><Link href="/experiences#explore-experiences" aria-current={!activeCategory ? "page" : undefined} className={`inline-flex min-h-11 items-center rounded-full border px-4 py-2 text-sm font-bold ${!activeCategory ? "border-[var(--accent)] bg-[var(--accent-soft)] text-[var(--accent-strong)]" : "border-[var(--line)] bg-white text-slate-600 hover:border-slate-300"}`}>All</Link>{MAHARASHTRA_EXPERIENCES.map((category) => <Link key={category.slug} href={`/experiences?category=${category.slug}${districtParam ? `&district=${encodeURIComponent(districtParam)}` : ""}#explore-experiences`} aria-current={activeCategory === category.slug ? "page" : undefined} className={`inline-flex min-h-11 items-center rounded-full border px-4 py-2 text-sm font-bold ${activeCategory === category.slug ? "border-[var(--accent)] bg-[var(--accent-soft)] text-[var(--accent-strong)]" : "border-[var(--line)] bg-white text-slate-600 hover:border-slate-300"}`}>{category.title}</Link>)}</nav>
            {directoryFailed && <p role="status" className="mt-6 rounded-xl border border-[var(--line)] bg-[var(--surface-muted)] px-4 py-3 text-sm text-slate-600">Live destination details could not be refreshed. Curated Maharashtra Tourist Places images and canonical district links are still available.</p>}
            <p aria-live="polite" className="mt-7 text-sm font-bold text-[var(--brand)]">{visible.length} destination idea{visible.length === 1 ? "" : "s"}</p>
            {visible.length ? <div className="mt-5 grid auto-rows-fr gap-5 sm:grid-cols-2 lg:grid-cols-3">{visible.map((destination) => {
              const district = districtBySlug.get(destination.districtSlug);
              return <article key={destination.city} className="group flex h-full flex-col overflow-hidden rounded-2xl border border-[var(--line)] bg-white shadow-[var(--shadow-sm)]"><div className="h-52 overflow-hidden bg-[var(--surface-muted)]"><DestinationImage src={district?.hero_image_url || destination.image} name={destination.city} className="transition duration-500 group-hover:scale-[1.025]" /></div><div className="flex flex-1 flex-col p-6"><p className="text-[10px] font-black uppercase tracking-[.14em] text-[var(--accent)]">{destination.experience} · {district?.division || destination.region}</p><h3 className="mt-2 text-2xl font-black tracking-tight text-[var(--brand)]">{destination.city}</h3><p className="mt-3 text-sm leading-6 text-slate-600">{district?.short_description || destination.descriptor}</p><p className="mt-4 border-t border-[var(--line)] pt-4 text-xs font-semibold leading-5 text-slate-500">{destination.attractions.join(" · ")}</p><div className="mt-auto flex flex-wrap gap-x-5 gap-y-3 pt-6"><Link href={`/destinations/${destination.districtSlug}`} className="text-sm font-black text-[var(--accent)] hover:text-[var(--accent-strong)]">Explore destination <span aria-hidden>→</span></Link><Link href={`/hotels?destination=${encodeURIComponent(destination.districtSlug)}&city=${encodeURIComponent(destination.city)}`} className="text-sm font-black text-[var(--brand)] hover:text-[var(--accent-strong)]">Find stays</Link></div></div></article>;
            })}</div> : <div className="mt-6 rounded-2xl border border-[var(--line)] bg-[var(--surface-muted)] p-9 text-center"><h3 className="text-lg font-black text-[var(--brand)]">No curated content matches both filters.</h3><p className="mt-2 text-sm text-slate-500">Choose another destination or clear the category filter.</p><Link href="/experiences#explore-experiences" className="primary-button mt-6">Clear filters</Link></div>}
          </div>
        </section>

        <section className="container-shell py-16 sm:py-20" aria-labelledby="culture-heading">
          <div className="max-w-3xl"><p className="eyebrow">Editorial discovery</p><h2 id="culture-heading" className="section-title mt-3">Go deeper than a destination card.</h2><p className="body-lead mt-4">Experiences remains the destination-led planning overview. Source-reviewed traditions and foodways now live in the interest guides, where statewide and regional stories do not need to become fake Places.</p></div>
          <div className="mt-9 grid gap-5 md:grid-cols-2">
            <article className="rounded-[1.4rem] border border-[var(--line)] bg-white p-7 shadow-[var(--shadow-sm)]"><p className="eyebrow">Living culture</p><h3 className="mt-3 text-2xl font-black text-[var(--brand)]">Culture & Traditions</h3><p className="mt-3 text-sm leading-7 text-slate-600">Read about pilgrimage, performance, Indigenous art, weaving and festival traditions with verified geographic context.</p><Link href="/explore/culture-traditions" className="mt-6 inline-flex text-sm font-black text-[var(--accent)]">Explore cultural stories <span aria-hidden className="ml-1">→</span></Link></article>
            <article className="rounded-[1.4rem] border border-[var(--line)] bg-white p-7 shadow-[var(--shadow-sm)]"><p className="eyebrow">Regional tables</p><h3 className="mt-3 text-2xl font-black text-[var(--brand)]">Food & Local Flavours</h3><p className="mt-3 text-sm leading-7 text-slate-600">Discover regional cuisines and festival food traditions without turning the guide into restaurant inventory or a recipe directory.</p><Link href="/explore/food-local-flavours" className="mt-6 inline-flex text-sm font-black text-[var(--accent)]">Explore regional flavours <span aria-hidden className="ml-1">→</span></Link></article>
          </div>
        </section>

        <section className="border-y border-[var(--line)] bg-[var(--surface-muted)] py-16 sm:py-20" aria-labelledby="wildlife-heading"><div className="container-shell"><div className="flex flex-col justify-between gap-6 sm:flex-row sm:items-end"><div className="max-w-2xl"><p className="eyebrow">Wildlife & nature</p><h2 id="wildlife-heading" className="section-title mt-3">Continue into the Safari catalogue</h2><p className="body-lead mt-4">Wildlife discovery begins here; availability requests, traveller details, pricing, and external confirmation stay within the existing Safari workflow.</p></div><Link href="/safaris" className="secondary-button shrink-0">Explore all safaris <span aria-hidden>→</span></Link></div><div className="mt-9"><SafariTeaser /></div></div></section>

        <section className="border-t border-[var(--line)] bg-white py-14"><div className="container-shell rounded-2xl bg-[var(--brand)] p-7 text-white sm:flex sm:items-center sm:justify-between sm:gap-8 sm:p-10"><div><p className="text-xs font-black uppercase tracking-[.16em] text-[var(--accent-on-dark)]">Plan your stay</p><h2 className="mt-3 text-2xl font-black tracking-tight">Use Maharashtra Tourist Places’ existing stay search.</h2><p className="mt-3 max-w-2xl text-sm leading-6 text-slate-200">Browse active hotels by canonical destination. Experience discovery does not create separate inventory, pricing, or payments.</p></div><Link href="/hotels" className="mt-6 inline-flex min-h-12 shrink-0 items-center justify-center rounded-xl bg-white px-5 text-sm font-black text-[var(--brand)] hover:bg-[var(--surface-muted)] sm:mt-0">Find stays <span aria-hidden className="ml-2">→</span></Link></div></section>
      </main>
    </>
  );
}
