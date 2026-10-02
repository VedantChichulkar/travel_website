import type { PublicDiscoveryStory } from "@/src/types/discovery-story";


const EDITORIAL_PRIMARY_SLUGS = ["culture-traditions", "food-local-flavours"];


export function primaryStoryInterest(story: PublicDiscoveryStory) {
  return story.interests.find((interest) => EDITORIAL_PRIMARY_SLUGS.includes(interest.slug)) ?? story.interests[0];
}
