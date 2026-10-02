import Link from "next/link";

import { Breadcrumbs } from "@/src/components/discovery/Breadcrumbs";
import { DiscoveryStoryCard } from "@/src/components/discovery/DiscoveryStoryCard";
import { DiscoveryStoryImage } from "@/src/components/discovery/DiscoveryStoryImage";
import { PlaceCard } from "@/src/components/discovery/PlaceCard";
import { primaryStoryInterest } from "@/src/lib/discovery-story-presentation";
import type { PublicDiscoveryStory, PublicDiscoveryStoryDetail } from "@/src/types/discovery-story";


export function DiscoveryStoryDetail({ story, relatedStories }: { story: PublicDiscoveryStoryDetail; relatedStories: PublicDiscoveryStory[] }) {
  const primaryInterest = primaryStoryInterest(story);
  const geography = story.districts.length ? story.districts.map((district) => district.name).join(" · ") : "Across Maharashtra";
  return (
    <main className="overflow-hidden bg-[#faf8f3]">
      <header className="border-b border-[#dfd8ca] bg-white">
        <div className="container-shell py-7"><Breadcrumbs items={[{ label: "Home", href: "/" }, { label: primaryInterest?.name ?? "Discover", href: primaryInterest?.path ?? "/destinations" }, { label: story.title }]} /></div>
        <div className="container-shell grid gap-10 pb-12 lg:grid-cols-[1.05fr_.95fr] lg:items-center lg:pb-16">
          <div className="max-w-3xl">
            <p className="eyebrow">{geography}</p>
            <h1 className="mt-4 text-balance font-serif text-5xl font-semibold leading-[.98] tracking-[-.04em] text-[var(--brand-strong)] sm:text-7xl">{story.title}</h1>
            <p className="mt-6 max-w-2xl text-lg leading-8 text-slate-600">{story.short_description}</p>
            <div className="mt-7 flex flex-wrap gap-2">{story.interests.map((interest) => <Link key={interest.slug} href={interest.path} className="inline-flex min-h-11 items-center rounded-full border border-[var(--line)] bg-white px-4 text-sm font-bold text-[var(--accent-strong)] hover:border-slate-300">{interest.name}</Link>)}</div>
          </div>
          <div className="relative aspect-[4/3] overflow-hidden rounded-[1.75rem] border border-[var(--line)] bg-[var(--surface-muted)] shadow-[var(--shadow-lg)]">
            <DiscoveryStoryImage story={story} eager />
          </div>
        </div>
      </header>

      <article className="container-shell py-16 sm:py-24">
        <div className="mx-auto max-w-3xl">
          <p className="eyebrow">The story</p>
          <h2 className="section-title mt-3">Context before you travel</h2>
          <p className="mt-7 whitespace-pre-line text-lg leading-9 text-slate-700">{story.body}</p>
        </div>
      </article>

      {story.districts.length > 0 && <section className="border-y border-[#e5dfd4] bg-white py-16" aria-labelledby="story-districts"><div className="container-shell"><p className="eyebrow">Associated geography</p><h2 id="story-districts" className="section-title mt-3">Explore related districts</h2><div className="mt-7 flex flex-wrap gap-3">{story.districts.map((district) => <Link key={district.slug} href={district.path} className="inline-flex min-h-12 items-center rounded-full border border-[var(--line)] bg-white px-5 text-sm font-black text-[var(--brand)] shadow-[var(--shadow-sm)] hover:bg-[var(--surface-muted)]">{district.name} <span aria-hidden className="ml-2 text-[var(--accent)]">→</span></Link>)}</div></div></section>}

      {story.related_places.length > 0 && <section className="container-shell py-16 sm:py-24" aria-labelledby="related-places"><div className="max-w-2xl"><p className="eyebrow">Continue through place</p><h2 id="related-places" className="section-title mt-3">Related places</h2><p className="body-lead mt-4">Geographic places with a direct, verified connection to this story.</p></div><div className="mt-9 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">{story.related_places.map((place) => <PlaceCard key={`${place.district.slug}-${place.slug}`} place={place} />)}</div></section>}

      {relatedStories.length > 0 && <section className="border-t border-[#e5dfd4] bg-white py-16 sm:py-24" aria-labelledby="related-discovery"><div className="container-shell"><p className="eyebrow">Related discovery</p><h2 id="related-discovery" className="section-title mt-3">Keep reading</h2><div className="mt-9 grid gap-5 md:grid-cols-3">{relatedStories.map((item) => <DiscoveryStoryCard key={item.slug} story={item} />)}</div></div></section>}
    </main>
  );
}
