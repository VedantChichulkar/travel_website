import Link from "next/link";

import { DiscoveryStoryImage } from "@/src/components/discovery/DiscoveryStoryImage";
import type { PublicDiscoveryStory } from "@/src/types/discovery-story";


export function DiscoveryStoryCard({ story }: { story: PublicDiscoveryStory }) {
  const location = story.districts.length
    ? story.districts.map((district) => district.name).join(" · ")
    : "Across Maharashtra";
  return (
    <article className="group flex h-full flex-col overflow-hidden rounded-[1.4rem] border border-[#dfd8ca] bg-white shadow-[var(--shadow-sm)]">
      <div className="relative h-56 overflow-hidden bg-[var(--surface-muted)]">
        <DiscoveryStoryImage story={story} className="transition duration-500 group-hover:scale-[1.025] motion-reduce:transition-none" />
      </div>
      <div className="flex flex-1 flex-col p-6">
        <p className="text-[10px] font-black uppercase tracking-[.16em] text-[var(--accent)]">{location}</p>
        <h3 className="mt-2 text-2xl font-black tracking-tight text-[var(--brand)]">{story.title}</h3>
        <p className="mt-3 text-sm leading-7 text-slate-600">{story.short_description}</p>
        <div className="mt-4 flex flex-wrap gap-1.5">{story.interests.map((interest) => <span key={interest.slug} className="rounded-full bg-[var(--accent-soft)] px-2.5 py-1 text-[10px] font-bold text-[var(--accent-strong)]">{interest.name}</span>)}</div>
        <Link href={story.path} className="mt-auto inline-flex pt-6 text-sm font-black text-[var(--accent)] hover:text-[var(--accent-strong)]">Read the story <span aria-hidden className="ml-1 transition-transform group-hover:translate-x-1">→</span></Link>
      </div>
    </article>
  );
}
