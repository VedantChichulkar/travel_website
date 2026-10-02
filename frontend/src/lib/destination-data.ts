import { notFound } from "next/navigation";

import { ApiError } from "@/src/services/api";
import { destinationService } from "@/src/services/destination.service";

export async function getDistrictOrNotFound(slug: string) {
  try {
    return await destinationService.getDistrict(slug);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) notFound();
    throw error;
  }
}

export async function getPlaceOrNotFound(districtSlug: string, destinationSlug: string) {
  try {
    return await destinationService.getPlace(districtSlug, destinationSlug);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) notFound();
    throw error;
  }
}
