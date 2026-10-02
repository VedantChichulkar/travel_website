import type { Metadata } from "next";

import { CanonicalPlaceDetail } from "@/src/components/discovery/CanonicalPlaceDetail";
import { getCanonicalPlaceOrNotFound, getInterests } from "@/src/lib/place-data";
import { resolvePlaceMedia } from "@/src/lib/discovery-media";

type PlacePageProps = { params: Promise<{ districtSlug: string; placeSlug: string }> };

export async function generateMetadata({ params }: PlacePageProps): Promise<Metadata> {
  const { districtSlug, placeSlug } = await params;
  const place = await getCanonicalPlaceOrNotFound(districtSlug, placeSlug);
  const description = place.short_description || place.description || undefined;
  const media = resolvePlaceMedia(place);
  return {
    title: `${place.name}, ${place.district.name}`,
    description,
    alternates: { canonical: place.path },
    openGraph: { title: `${place.name}, ${place.district.name}`, description, url: place.path, images: [{ url: media.src, alt: media.alt }] },
  };
}

export default async function PlacePage({ params }: PlacePageProps) {
  const { districtSlug, placeSlug } = await params;
  const [place, interests] = await Promise.all([
    getCanonicalPlaceOrNotFound(districtSlug, placeSlug),
    getInterests(),
  ]);
  return <CanonicalPlaceDetail place={place} relatedPlaces={place.related_places} allInterests={interests.items} />;
}
