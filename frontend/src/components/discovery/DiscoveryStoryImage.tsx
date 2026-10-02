import { DiscoveryMediaImage } from "@/src/components/discovery/DiscoveryMediaImage";
import { resolveStoryMedia } from "@/src/lib/discovery-media";
import type { PublicDiscoveryStory } from "@/src/types/discovery-story";


export function DiscoveryStoryImage({
  story,
  className = "",
  eager = false,
}: {
  story: PublicDiscoveryStory;
  className?: string;
  eager?: boolean;
}) {
  return <DiscoveryMediaImage media={resolveStoryMedia(story)} priority={eager} sizes="(min-width: 1024px) 50vw, 100vw" className={className} />;
}
