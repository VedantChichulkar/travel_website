import type { Metadata } from "next";

import { DiscoveryStoryDetail } from "@/src/components/discovery/DiscoveryStoryDetail";
import { getDiscoveryStoryOrNotFound } from "@/src/lib/discovery-story-data";
import { resolveStoryMedia } from "@/src/lib/discovery-media";
import { primaryStoryInterest } from "@/src/lib/discovery-story-presentation";
import { discoveryStoryService } from "@/src/services/discovery-story.service";


type StoryPageProps = { params: Promise<{ storySlug: string }> };


export async function generateMetadata({ params }: StoryPageProps): Promise<Metadata> {
  const { storySlug } = await params;
  const story = await getDiscoveryStoryOrNotFound(storySlug);
  const media = resolveStoryMedia(story);
  return {
    title: story.title,
    description: story.short_description,
    alternates: { canonical: story.path },
    openGraph: { title: story.title, description: story.short_description, url: story.path, images: [{ url: media.src, alt: media.alt }] },
  };
}


export default async function StoryPage({ params }: StoryPageProps) {
  const { storySlug } = await params;
  const story = await getDiscoveryStoryOrNotFound(storySlug);
  const primaryInterest = primaryStoryInterest(story)?.slug;
  const related = primaryInterest
    ? await discoveryStoryService.listStories({ interest: primaryInterest, limit: 4 })
    : { items: [], total: 0 };
  return <DiscoveryStoryDetail story={story} relatedStories={related.items.filter((item) => item.slug !== story.slug).slice(0, 3)} />;
}
