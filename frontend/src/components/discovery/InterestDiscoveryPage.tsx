import Image from "next/image";
import Link from "next/link";

import { Breadcrumbs } from "@/src/components/discovery/Breadcrumbs";
import { DiscoveryStoryCard } from "@/src/components/discovery/DiscoveryStoryCard";
import { InterestCard } from "@/src/components/discovery/InterestCard";
import { PlaceCard } from "@/src/components/discovery/PlaceCard";
import { interestVisual } from "@/src/data/place-interests";
import type { PublicDiscoveryStoryList } from "@/src/types/discovery-story";
import type { PublicInterest, PublicPlaceList } from "@/src/types/place";


export function InterestDiscoveryPage({
  interest,
  interests,
  places,
  stories,
}: {
  interest: PublicInterest;
  interests: PublicInterest[];
  places: PublicPlaceList;
  stories: PublicDiscoveryStoryList;
}) {
  const visual = interestVisual(interest.slug);
  const editorialPrimary = interest.slug === "culture-traditions" || interest.slug === "food-local-flavours";
  const districtGroups = [...new Map([
    ...places.items.map((place) => [place.district.slug, place.district] as const),
    ...stories.items.flatMap((story) => story.districts.map((district) => [district.slug, district] as const)),
  ]).values()];
  const relatedSlugs = visual?.related ?? [];
  const relatedSlugSet = new Set<string>(relatedSlugs);
  const related = [
    ...relatedSlugs.map((slug) => interests.find((item) => item.slug === slug)).filter((item): item is PublicInterest => Boolean(item)),
    ...interests.filter((item) => item.slug !== interest.slug && !relatedSlugSet.has(item.slug)),
  ].slice(0, 3);
  const introduction = interest.description || visual?.description;
  const firstSection = editorialPrimary && stories.items.length > 0 ? "stories" : "places";

  return (
    <main className="overflow-hidden bg-[#faf8f3]">
      <header className="relative isolate min-h-[34rem] bg-[var(--brand-strong)] text-white sm:min-h-[39rem]">
        {visual && <Image src={visual.image} alt={visual.imageAlt} fill unoptimized loading="eager" fetchPriority="high" sizes="100vw" className="object-cover" style={{ objectPosition: visual.objectPosition }} />}
        <div className="absolute inset-0 bg-gradient-to-r from-[#071725]/95 via-[#071725]/62 to-[#071725]/15" aria-hidden />
        <div className="absolute inset-0 bg-gradient-to-t from-[#071725]/90 via-transparent to-black/25" aria-hidden />
        <div className="container-shell relative flex min-h-[34rem] flex-col justify-between py-8 sm:min-h-[39rem] sm:py-10">
          <Breadcrumbs tone="dark" items={[{ label: "Home", href: "/" }, { label: "Explore", href: "/destinations#explore-by-interest" }, { label: interest.name }]} />
          <div className="max-w-3xl pb-5 sm:pb-10">
            <p className="text-xs font-black uppercase tracking-[.2em] text-[#c9e1f5]">{visual?.eyebrow ?? "Explore Maharashtra"}</p>
            <h1 className="mt-4 text-balance font-serif text-5xl font-semibold leading-[.96] tracking-[-.045em] sm:text-7xl">{interest.name}</h1>
            {introduction && <p className="mt-6 max-w-2xl text-base leading-8 text-white/80 sm:text-lg">{introduction}</p>}
            <a href={`#${firstSection}`} className="mt-8 inline-flex min-h-12 items-center rounded-full bg-white px-6 text-sm font-black text-[var(--brand)] hover:bg-[var(--surface-muted)]">{firstSection === "stories" ? "Explore stories" : "Explore available places"} <span aria-hidden className="ml-2">↓</span></a>
          </div>
        </div>
      </header>

      {editorialPrimary && stories.items.length > 0 && <StorySection stories={stories} interest={interest} />}
      {(places.items.length > 0 || stories.items.length === 0) && <PlaceSection places={places} interest={interest} />}
      {!editorialPrimary && stories.items.length > 0 && <StorySection stories={stories} interest={interest} />}

      {districtGroups.length > 0 && <section className="border-y border-[#e5dfd4] bg-white py-16 sm:py-20" aria-labelledby="districts-title"><div className="container-shell"><p className="eyebrow">Explore by district</p><h2 id="districts-title" className="section-title mt-3">Where this discovery connects</h2><div className="mt-8 flex flex-wrap gap-3">{districtGroups.map((district) => <Link key={district.slug} href={district.path} className="inline-flex min-h-12 items-center rounded-full border border-[var(--line)] bg-white px-5 text-sm font-black text-[var(--brand)] shadow-[var(--shadow-sm)] hover:border-slate-300 hover:bg-[var(--surface-muted)]">{district.name} <span aria-hidden className="ml-2 text-[var(--accent)]">→</span></Link>)}</div></div></section>}

      {related.length > 0 && <section className="container-shell py-16 sm:py-24" aria-labelledby="related-title"><div className="max-w-2xl"><p className="eyebrow">Continue exploring</p><h2 id="related-title" className="section-title mt-3">More ways into Maharashtra</h2></div><div className="mt-9 grid gap-5 md:grid-cols-3">{related.map((item) => <InterestCard key={item.slug} interest={item} />)}</div></section>}

      <section className="border-t border-[var(--line)] bg-white py-14"><div className="container-shell rounded-[1.5rem] bg-[var(--brand)] p-7 text-white sm:flex sm:items-center sm:justify-between sm:gap-8 sm:p-10"><div><p className="text-xs font-black uppercase tracking-[.16em] text-[var(--accent-on-dark)]">Maharashtra by location</p><h2 className="mt-3 text-2xl font-black tracking-tight">Prefer to start with a district?</h2><p className="mt-3 max-w-2xl text-sm leading-6 text-slate-200">Return to the complete 36-district directory and continue through Maharashtra Tourist Places’ canonical destination routes.</p></div><Link href="/destinations#district-directory" className="mt-6 inline-flex min-h-12 shrink-0 items-center justify-center rounded-xl bg-white px-5 text-sm font-black text-[var(--brand)] hover:bg-[var(--surface-muted)] sm:mt-0">Explore all districts <span aria-hidden className="ml-2">→</span></Link></div></section>
    </main>
  );
}


function StorySection({ stories, interest }: { stories: PublicDiscoveryStoryList; interest: PublicInterest }) {
  const food = interest.slug === "food-local-flavours";
  return (
    <section id="stories" className="scroll-mt-20 py-16 sm:py-24" aria-labelledby="stories-title">
      <div className="container-shell">
        <div className="flex flex-col justify-between gap-5 sm:flex-row sm:items-end">
          <div className="max-w-2xl"><p className="eyebrow">{food ? "Regional flavours" : "Stories & traditions"}</p><h2 id="stories-title" className="section-title mt-3">{food ? "Discover Maharashtra’s foodways" : "Explore living culture"}</h2><p className="body-lead mt-4">Source-reviewed introductions with regional context and no invented geographic ownership.</p></div>
          <p className="text-sm font-bold text-slate-500">{stories.total} published stor{stories.total === 1 ? "y" : "ies"}</p>
        </div>
        <div className="mt-9 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">{stories.items.map((story) => <DiscoveryStoryCard key={story.slug} story={story} />)}</div>
      </div>
    </section>
  );
}


function PlaceSection({ places, interest }: { places: PublicPlaceList; interest: PublicInterest }) {
  return (
    <section id="places" className="scroll-mt-20 border-t border-[#e5dfd4] py-16 sm:py-24" aria-labelledby="places-title">
      <div className="container-shell">
        <div className="flex flex-col justify-between gap-5 sm:flex-row sm:items-end"><div className="max-w-2xl"><p className="eyebrow">Available places</p><h2 id="places-title" className="section-title mt-3">Places to begin</h2>{places.items.length > 0 && <p className="body-lead mt-4">Published geographic places classified under {interest.name.toLocaleLowerCase("en-IN")}.</p>}</div>{places.total > 0 && <p className="text-sm font-bold text-slate-500">{places.total} published place{places.total === 1 ? "" : "s"}</p>}</div>
        {places.items.length > 0 ? <div className="mt-9 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">{places.items.map((place) => <PlaceCard key={`${place.district.slug}-${place.slug}`} place={place} />)}</div> : <div className="mt-9 overflow-hidden rounded-[1.5rem] border border-[#dfd8ca] bg-white p-7 shadow-[var(--shadow-sm)] sm:grid sm:grid-cols-[1fr_auto] sm:items-center sm:gap-10 sm:p-10"><div><p className="text-xs font-black uppercase tracking-[.16em] text-[var(--accent)]">A considered directory</p><h3 className="mt-3 text-2xl font-black tracking-tight text-[var(--brand)]">No geographic places are classified here yet.</h3><p className="mt-3 max-w-2xl text-sm leading-7 text-slate-600">Place remains reserved for visitable locations. Explore the verified stories above or browse Maharashtra by district.</p></div><Link href="/destinations#district-directory" className="primary-button mt-6 shrink-0 sm:mt-0">Browse districts <span aria-hidden>→</span></Link></div>}
      </div>
    </section>
  );
}
