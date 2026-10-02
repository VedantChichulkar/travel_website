import { notFound } from "next/navigation";

import { ApiError } from "@/src/services/api";
import { discoveryStoryService } from "@/src/services/discovery-story.service";


export async function getDiscoveryStoryOrNotFound(slug: string) {
  try {
    return await discoveryStoryService.getStory(slug);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) notFound();
    throw error;
  }
}
