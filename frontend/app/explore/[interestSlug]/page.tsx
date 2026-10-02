import type { Metadata } from "next";

import { InterestDiscoveryPage } from "@/src/components/discovery/InterestDiscoveryPage";
import { interestVisual } from "@/src/data/place-interests";
import { getInterestOrNotFound } from "@/src/lib/place-data";
import { discoveryStoryService } from "@/src/services/discovery-story.service";
import { placeService } from "@/src/services/place.service";

type InterestPageProps = {
  params: Promise<{ interestSlug: string }>;
  searchParams: Promise<{ district?: string | string[] }>;
};

export async function generateMetadata({ params }: InterestPageProps): Promise<Metadata> {
  const { interestSlug } = await params;
  const { interest } = await getInterestOrNotFound(interestSlug);
  const visual = interestVisual(interest.slug);
  const description = interest.description || visual?.description;
  return {
    title: `${interest.name} in Maharashtra`,
    description,
    alternates: { canonical: interest.path },
    openGraph: { title: `${interest.name} in Maharashtra`, description, url: interest.path, images: visual ? [{ url: visual.image, alt: visual.imageAlt }] : undefined },
  };
}

export default async function InterestPage({ params, searchParams }: InterestPageProps) {
  const { interestSlug } = await params;
  const rawDistrict = (await searchParams).district;
  const district = Array.isArray(rawDistrict) ? rawDistrict[0] : rawDistrict;
  const [{ interest, interests }, places, stories] = await Promise.all([
    getInterestOrNotFound(interestSlug),
    placeService.listPlaces({ interest: interestSlug, district, limit: 100 }),
    discoveryStoryService.listStories({ interest: interestSlug, district, limit: 100 }),
  ]);
  return <InterestDiscoveryPage interest={interest} interests={interests.items} places={places} stories={stories} />;
}
