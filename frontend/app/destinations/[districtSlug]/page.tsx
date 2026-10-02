import type { Metadata } from "next";

import { DistrictDetail } from "@/src/components/destinations/DistrictDetail";
import { getDistrictOrNotFound } from "@/src/lib/destination-data";
import { placeService } from "@/src/services/place.service";

type DistrictPageProps = { params: Promise<{ districtSlug: string }> };

export async function generateMetadata({ params }: DistrictPageProps): Promise<Metadata> {
  const { districtSlug } = await params;
  const district = await getDistrictOrNotFound(districtSlug);
  const description = district.short_description || `Explore active destinations and stays in ${district.name} district, Maharashtra.`;
  return {
    title: `${district.name} District`,
    description,
    alternates: { canonical: district.path },
    openGraph: { title: `${district.name} District`, description, url: district.path, images: district.hero_image_url ? [{ url: district.hero_image_url, alt: `${district.name} district` }] : undefined },
  };
}

export default async function DistrictPage({ params }: DistrictPageProps) {
  const { districtSlug } = await params;
  const [district, places] = await Promise.all([
    getDistrictOrNotFound(districtSlug),
    placeService.listPlaces({ district: districtSlug, limit: 12 }).catch(() => null),
  ]);
  return <DistrictDetail district={district} places={places} />;
}
