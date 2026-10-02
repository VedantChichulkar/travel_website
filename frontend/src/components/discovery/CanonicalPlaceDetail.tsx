import Link from "next/link";

import { Breadcrumbs } from "@/src/components/discovery/Breadcrumbs";
import { InterestCard } from "@/src/components/discovery/InterestCard";
import { PlaceCard } from "@/src/components/discovery/PlaceCard";
import { DiscoveryMediaImage } from "@/src/components/discovery/DiscoveryMediaImage";
import { DiscoveryFAQs, DiscoveryGallery } from "@/src/components/discovery/RichDiscoverySections";
import { DestinationSafaris } from "@/src/components/safari/DestinationSafaris";
import { SPIRITUAL_TRADITION_LABELS } from "@/src/data/place-interests";
import { placeStayPath } from "@/src/lib/place-routes";
import { resolvePlaceMedia } from "@/src/lib/discovery-media";
import type { PublicInterest, PublicPlace, PublicPlaceDetail } from "@/src/types/place";

export function CanonicalPlaceDetail({ place, relatedPlaces, allInterests }: { place: PublicPlaceDetail; relatedPlaces: PublicPlace[]; allInterests: PublicInterest[] }) {
  const hotelHref = placeStayPath({
    districtSlug: place.district.slug,
    districtName: place.district.name,
    destinationSlug: place.destination?.slug,
    destinationName: place.destination?.name,
  });
  const wildlife = place.interests.some((interest) => interest.slug === "wildlife-forests");
  const relatedInterests = place.interests.map((interest) => allInterests.find((item) => item.slug === interest.slug)).filter((item): item is PublicInterest => Boolean(item));
  const tradition = place.spiritual_tradition ? SPIRITUAL_TRADITION_LABELS[place.spiritual_tradition] : null;
  const media = resolvePlaceMedia(place);
  const visitorRows = [
    ["Address", place.address], ["Opening hours", place.opening_hours], ["Entry fee", place.entry_fee_info],
    ["Recommended duration", place.recommended_visit_duration], ["Best time to visit", place.best_time_to_visit],
  ].filter((row): row is [string, string] => Boolean(row[1]));
  const travelRows = [["Nearest railway station", place.nearest_railway_station], ["Nearest airport", place.nearest_airport]].filter((row): row is [string, string] => Boolean(row[1]));

  return (
    <main className="overflow-hidden bg-[#faf8f3]">
      <header className="border-b border-[#e5dfd4] bg-white">
        <div className="container-shell py-7"><Breadcrumbs items={[{ label: "Home", href: "/" }, { label: "Destinations", href: "/destinations" }, { label: place.district.name, href: place.district.path }, ...(place.destination ? [{label: place.destination.name, href: place.destination.path}] : []), { label: place.name }]} /></div>
        <div className="container-shell grid gap-9 pb-12 lg:grid-cols-[.88fr_1.12fr] lg:items-center lg:pb-16">
          <div className="max-w-2xl">
            <p className="eyebrow">{place.destination?.name ?? `${place.district.name} district`}</p>
            <h1 className="page-title mt-3 text-balance">{place.name}</h1>
            {place.short_description && <p className="body-lead mt-5">{place.short_description}</p>}
            <div className="mt-6 flex flex-wrap gap-2">{place.interests.map((interest) => <Link key={interest.slug} href={interest.path} className="inline-flex min-h-9 items-center rounded-full bg-[var(--accent-soft)] px-3 text-xs font-black text-[var(--accent-strong)] hover:bg-[#dcebf8]">{interest.name}</Link>)}{tradition && <span className="inline-flex min-h-9 items-center rounded-full border border-[#ded6c8] bg-[#f8f3e9] px-3 text-xs font-black text-[#765a2c]">{tradition}</span>}</div>
            <div className="mt-8 flex flex-wrap gap-3"><Link href={hotelHref} className="primary-button">Find stays <span aria-hidden>→</span></Link><Link href={place.district.path} className="secondary-button">Explore {place.district.name}</Link></div>
          </div>
          <div className="relative h-80 overflow-hidden rounded-[1.5rem] border border-[var(--line)] bg-[var(--surface-muted)] shadow-[var(--shadow-sm)] sm:h-[30rem]"><DiscoveryMediaImage media={media} priority sizes="(max-width: 1024px) 100vw, 55vw" /></div>
        </div>
      </header>

      <div className="container-shell py-16 sm:py-24">
        {place.description && <section aria-labelledby="place-about" className="max-w-3xl"><p className="eyebrow">About</p><h2 id="place-about" className="section-title mt-3">About {place.name}</h2><p className="mt-6 whitespace-pre-wrap text-base leading-8 text-slate-600">{place.description}</p></section>}

        <DiscoveryGallery name={place.name} media={place.gallery} />

        {visitorRows.length > 0 && <section className="mt-20" aria-labelledby="visitor-info"><p className="eyebrow">Plan your visit</p><h2 id="visitor-info" className="section-title mt-3">Visitor information</h2><dl className="mt-8 grid gap-4 sm:grid-cols-2">{visitorRows.map(([label, value]) => <div key={label} className="rounded-2xl border border-[var(--line)] bg-white p-5"><dt className="text-xs font-black uppercase tracking-[.14em] text-[var(--accent)]">{label}</dt><dd className="mt-2 whitespace-pre-wrap text-sm leading-7 text-slate-600">{value}</dd></div>)}</dl>{(place.visitor_info_source || place.visitor_info_verified_at) && <p className="mt-4 text-xs text-slate-500">Source: {place.visitor_info_source_url ? <a href={place.visitor_info_source_url} rel="noreferrer" target="_blank" className="font-bold underline">{place.visitor_info_source || "Reference"}</a> : place.visitor_info_source}{place.visitor_info_verified_at ? ` · Last verified ${place.visitor_info_verified_at}` : ""}. Details may change; confirm before travel.</p>}</section>}

        {(place.getting_there || travelRows.length > 0) && <section className="mt-20 max-w-4xl" aria-labelledby="getting-there"><p className="eyebrow">Travel guidance</p><h2 id="getting-there" className="section-title mt-3">Getting there</h2>{place.getting_there && <p className="mt-6 whitespace-pre-wrap text-base leading-8 text-slate-600">{place.getting_there}</p>}{travelRows.length > 0 && <dl className="mt-7 grid gap-4 sm:grid-cols-2">{travelRows.map(([label, value]) => <div key={label} className="rounded-2xl border border-[var(--line)] bg-white p-5"><dt className="text-xs font-black uppercase tracking-[.14em] text-[var(--accent)]">{label}</dt><dd className="mt-2 text-sm leading-7 text-slate-600">{value}</dd></div>)}</dl>}</section>}

        {relatedPlaces.length > 0 && <section className={place.description ? "mt-20" : ""} aria-labelledby="nearby-title"><div className="max-w-2xl"><p className="eyebrow">Explore nearby</p><h2 id="nearby-title" className="section-title mt-3">More places in {place.district.name}</h2><p className="body-lead mt-4">Continue through other published places in the same district.</p></div><div className="mt-9 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">{relatedPlaces.map((item) => <PlaceCard key={`${item.district.slug}-${item.slug}`} place={item} />)}</div></section>}

        {wildlife && place.destination && <DestinationSafaris districtSlug={place.district.slug} destinationSlug={place.destination.slug} heading={`Safaris connected to ${place.destination.name}`} />}

        <section className="mt-20 overflow-hidden rounded-[1.5rem] bg-[var(--brand)] p-7 text-white sm:flex sm:items-center sm:justify-between sm:gap-10 sm:p-10" aria-labelledby="place-stays"><div><p className="text-xs font-black uppercase tracking-[.16em] text-[var(--accent-on-dark)]">Where to stay</p><h2 id="place-stays" className="mt-3 text-3xl font-black tracking-tight">Find stays through {place.destination?.name ?? place.district.name}</h2><p className="mt-3 max-w-2xl text-sm leading-7 text-slate-200">Maharashtra Tourist Places uses this place’s canonical {place.destination ? "destination" : "district"} relationship. No distance or proximity claim is implied.</p></div><Link href={hotelHref} className="mt-6 inline-flex min-h-12 shrink-0 items-center justify-center rounded-xl bg-white px-5 text-sm font-black text-[var(--brand)] hover:bg-[var(--surface-muted)] sm:mt-0">Search hotels <span aria-hidden className="ml-2">→</span></Link></section>

        <DiscoveryFAQs name={place.name} faqs={place.faqs} />

        {relatedInterests.length > 0 && <section className="mt-20" aria-labelledby="place-interests"><div className="max-w-2xl"><p className="eyebrow">Keep exploring</p><h2 id="place-interests" className="section-title mt-3">Discover by interest</h2></div><div className="mt-9 grid gap-5 md:grid-cols-3">{relatedInterests.slice(0, 3).map((interest) => <InterestCard key={interest.slug} interest={interest} />)}</div></section>}
      </div>
    </main>
  );
}
