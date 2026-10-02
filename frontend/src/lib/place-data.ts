import { notFound } from "next/navigation";

import { ApiError } from "@/src/services/api";
import { placeService } from "@/src/services/place.service";

export async function getInterests() {
  return placeService.listInterests();
}

export async function getInterestOrNotFound(slug: string) {
  const interests = await getInterests();
  const interest = interests.items.find((item) => item.slug === slug);
  if (!interest) notFound();
  return { interest, interests };
}

export async function getCanonicalPlaceOrNotFound(districtSlug: string, placeSlug: string) {
  try {
    return await placeService.getPlace(districtSlug, placeSlug);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) notFound();
    throw error;
  }
}

