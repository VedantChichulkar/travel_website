import Link from "next/link";

import { DestinationImage } from "@/src/components/destinations/DestinationImage";
import { DestinationCulture } from "@/src/components/destinations/DestinationCulture";
import { DestinationSafaris } from "@/src/components/safari/DestinationSafaris";
import { PlaceCard } from "@/src/components/discovery/PlaceCard";
import { curatedDestinationForDistrict } from "@/src/data/maharashtra-destinations";
import type { PublicDistrictDetail } from "@/src/types/destination";
import type { PublicPlaceList } from "@/src/types/place";

export function DistrictDetail({ district, places }: { district: PublicDistrictDetail; places: PublicPlaceList | null }) {
  const hotelHref = `/hotels?destination=${encodeURIComponent(district.slug)}&city=${encodeURIComponent(district.name)}`;
  const heroImage = district.hero_image_url || curatedDestinationForDistrict(district.slug)?.image || null;
  const representedInterests = places ? [...new Map(places.items.flatMap((place) => place.interests).map((interest) => [interest.slug, interest])).values()] : [];
  return (
    <>
      <header className="border-b border-[var(--line)] bg-white">
        <div className="container-shell py-8"><Link href="/destinations" className="text-sm font-black text-[var(--accent)] hover:text-[var(--accent-strong)]">← All destinations</Link></div>
        <div className="container-shell grid gap-8 pb-12 lg:grid-cols-[.9fr_1.1fr] lg:items-center">
          <div>
            <p className="eyebrow">{district.division} division</p>
            <h1 className="page-title mt-3">{district.name}</h1>
            {district.short_description && <p className="body-lead mt-5">{district.short_description}</p>}
            <Link href={hotelHref} className="primary-button mt-7">Find stays in {district.name} <span aria-hidden>→</span></Link>
          </div>
          <div className="h-72 overflow-hidden rounded-2xl border border-[var(--line)] bg-[var(--surface-muted)] sm:h-96"><DestinationImage src={heroImage} name={`${district.name} district`} priority /></div>
        </div>
      </header>

      <main className="container-shell py-14 sm:py-18">
        {district.short_description && <section aria-labelledby="district-about" className="max-w-3xl"><p className="eyebrow">About the district</p><h2 id="district-about" className="section-title mt-3">About {district.name}</h2><p className="mt-5 whitespace-pre-wrap text-base leading-8 text-slate-600">{district.short_description}</p></section>}

        <section aria-labelledby="destinations-heading" className={district.short_description ? "mt-16" : ""}>
          <div className="max-w-2xl"><p className="eyebrow">Destinations</p><h2 id="destinations-heading" className="section-title mt-3">Explore destinations in {district.name}</h2><p className="body-lead mt-4">Continue into the towns, areas and destination records currently available in Maharashtra Tourist Places.</p></div>
          {district.destinations.length ? <div className="mt-9 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">{district.destinations.map((place) => <article key={place.slug} className="group overflow-hidden rounded-2xl border border-[var(--line)] bg-white shadow-[var(--shadow-sm)]"><div className="h-48 overflow-hidden bg-[var(--surface-muted)]"><DestinationImage src={place.image_url} name={place.name} alt={place.image_alt} className="transition duration-500 group-hover:scale-[1.025]" /></div><div className="p-5"><h3 className="text-xl font-black text-[var(--brand)]">{place.name}</h3>{place.description && <p className="mt-3 line-clamp-3 text-sm leading-6 text-slate-600">{place.description}</p>}<Link href={place.path} className="mt-5 inline-flex text-sm font-black text-[var(--accent)] hover:text-[var(--accent-strong)]">Explore place <span aria-hidden className="ml-1">→</span></Link></div></article>)}</div> : <div className="mt-8 rounded-2xl border border-[var(--line)] bg-[var(--surface-muted)] p-8 text-center"><p className="font-bold text-[var(--brand)]">No destination records have been published for this district yet.</p><p className="mt-2 text-sm text-slate-500">You can still search active stays across the district.</p></div>}
        </section>

        {places?.items.length ? <section className="mt-18" aria-labelledby="top-places-heading"><div className="max-w-2xl"><p className="eyebrow">Top places to visit</p><h2 id="top-places-heading" className="section-title mt-3">Published attractions in {district.name}</h2><p className="body-lead mt-4">Canonical Place records connected to this district.</p></div><div className="mt-9 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">{places.items.map((place) => <PlaceCard key={`${place.district.slug}-${place.slug}`} place={place} />)}</div></section> : places === null ? <p role="status" className="mt-12 rounded-xl border border-[var(--line)] bg-[var(--surface-muted)] px-4 py-3 text-sm text-slate-600">Published attractions could not be refreshed. District destinations and stay discovery remain available.</p> : null}

        {representedInterests.length > 0 && <section className="mt-18" aria-labelledby="district-interest-heading"><p className="eyebrow">Explore by interest</p><h2 id="district-interest-heading" className="section-title mt-3">Discover {district.name} your way</h2><div className="mt-7 flex flex-wrap gap-3">{representedInterests.map((interest) => <Link key={interest.slug} href={`${interest.path}?district=${encodeURIComponent(district.slug)}`} className="inline-flex min-h-12 items-center rounded-full border border-[var(--line)] bg-white px-5 text-sm font-black text-[var(--brand)] shadow-[var(--shadow-sm)] hover:border-slate-300 hover:bg-[var(--surface-muted)]">{interest.name} <span aria-hidden className="ml-2 text-[var(--accent)]">→</span></Link>)}</div></section>}

        <DestinationCulture districtSlug={district.slug} />

        <DestinationSafaris districtSlug={district.slug} heading={`Safaris in ${district.name}`} />

        <section aria-labelledby="stays-heading" className="mt-16 rounded-2xl border border-[var(--line)] bg-white p-7 sm:flex sm:items-center sm:justify-between sm:gap-8 sm:p-9">
          <div><p className="eyebrow">Where to stay</p><h2 id="stays-heading" className="mt-3 text-2xl font-black tracking-tight text-[var(--brand)]">Find stays in {district.name}</h2><p className="mt-3 max-w-2xl text-sm leading-6 text-slate-600">Search Maharashtra Tourist Places’ active hotel catalogue using this district’s canonical destination filter.</p></div>
          <Link href={hotelHref} className="primary-button mt-6 shrink-0 sm:mt-0">Search hotels <span aria-hidden>→</span></Link>
        </section>
      </main>
    </>
  );
}
