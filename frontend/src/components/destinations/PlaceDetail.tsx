import Link from "next/link";

import { DestinationImage } from "@/src/components/destinations/DestinationImage";
import { Breadcrumbs } from "@/src/components/discovery/Breadcrumbs";
import { PlaceCard } from "@/src/components/discovery/PlaceCard";
import { DiscoveryFAQs, DiscoveryGallery } from "@/src/components/discovery/RichDiscoverySections";
import { DestinationSafaris } from "@/src/components/safari/DestinationSafaris";
import type { PublicDestinationDetail } from "@/src/types/destination";

export function PlaceDetail({ place }: { place: PublicDestinationDetail }) {
  const canonicalFilter = `${place.district_slug}/${place.slug}`;
  const hotelHref = `/hotels?destination=${encodeURIComponent(canonicalFilter)}&city=${encodeURIComponent(place.name)}`;
  return (
    <>
      <header className="border-b border-[var(--line)] bg-white">
        <div className="container-shell py-8"><Breadcrumbs items={[{label: "Home", href: "/"}, {label: "Destinations", href: "/destinations"}, {label: place.district_name, href: `/destinations/${place.district_slug}`}, {label: place.name}]} /></div>
        <div className="container-shell grid gap-8 pb-12 lg:grid-cols-[.9fr_1.1fr] lg:items-center">
          <div><p className="eyebrow">{place.district_name} district</p><h1 className="page-title mt-3">{place.name}</h1>{(place.short_summary || place.description) && <p className="body-lead mt-5">{place.short_summary || place.description}</p>}<Link href={hotelHref} className="primary-button mt-7">Find stays near {place.name} <span aria-hidden>→</span></Link></div>
          <div className="h-72 overflow-hidden rounded-2xl border border-[var(--line)] bg-[var(--surface-muted)] sm:h-96"><DestinationImage src={place.image_url} name={place.name} alt={place.image_alt} priority /></div>
        </div>
      </header>
      <main className="container-shell py-14 sm:py-18">
        {place.description && <section className="max-w-3xl" aria-labelledby="place-about"><p className="eyebrow">About this place</p><h2 id="place-about" className="section-title mt-3">About {place.name}</h2><p className="mt-5 whitespace-pre-wrap text-base leading-8 text-slate-600">{place.description}</p></section>}
        <DiscoveryGallery name={place.name} media={place.gallery} />
        {place.places.length > 0 && <section className="mt-20" aria-labelledby="destination-places"><p className="eyebrow">Places to visit</p><h2 id="destination-places" className="section-title mt-3">Explore {place.name}</h2><p className="body-lead mt-4 max-w-2xl">Published places assigned to {place.name} appear here automatically.</p><div className="mt-9 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">{place.places.map((item) => <PlaceCard key={item.path} place={item} />)}</div></section>}
        <DestinationSafaris districtSlug={place.district_slug} destinationSlug={place.slug} heading={`Safaris near ${place.name}`} />
        <section className="mt-16 rounded-2xl border border-[var(--line)] bg-white p-7 sm:flex sm:items-center sm:justify-between sm:gap-8 sm:p-9"><div><p className="eyebrow">Where to stay</p><h2 className="mt-3 text-2xl font-black tracking-tight text-[var(--brand)]">Find stays near {place.name}</h2><p className="mt-3 max-w-2xl text-sm leading-6 text-slate-600">Search active properties using this place’s canonical destination path.</p></div><Link href={hotelHref} className="primary-button mt-6 shrink-0 sm:mt-0">Search hotels <span aria-hidden>→</span></Link></section>
        <DiscoveryFAQs name={place.name} faqs={place.faqs} />
      </main>
    </>
  );
}
