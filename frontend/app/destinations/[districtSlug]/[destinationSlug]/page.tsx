import type { Metadata } from "next";

import { PlaceDetail } from "@/src/components/destinations/PlaceDetail";
import { getPlaceOrNotFound } from "@/src/lib/destination-data";

type DestinationPageProps = { params: Promise<{ districtSlug: string; destinationSlug: string }> };

export async function generateMetadata({ params }: DestinationPageProps): Promise<Metadata> {
  const { districtSlug, destinationSlug } = await params;
  const place = await getPlaceOrNotFound(districtSlug, destinationSlug);
  const description = place.short_summary || place.description || `Explore ${place.name} in ${place.district_name} district and find active stays through Maharashtra Tourist Places.`;
  return {
    title: `${place.name}, ${place.district_name}`,
    description,
    alternates: { canonical: place.path },
    openGraph: { title: `${place.name}, ${place.district_name}`, description, url: place.path, images: place.image_url ? [{ url: place.image_url, alt: place.image_alt || place.name }] : undefined },
  };
}

export default async function DestinationPage({ params }: DestinationPageProps) {
  const { districtSlug, destinationSlug } = await params;
  const place = await getPlaceOrNotFound(districtSlug, destinationSlug);
  return <PlaceDetail place={place} />;
}
