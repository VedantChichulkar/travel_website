import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { HotelDetailView } from "@/src/components/HotelDetailView";
import { parseHotelSearch } from "@/src/lib/hotel-search";
import { hotelService } from "@/src/services/hotel.service";
import { ApiError } from "@/src/services/api";
import type { HotelDetail } from "@/src/types/hotel";

export async function generateMetadata({ params }: PageProps<"/hotels/[id]">): Promise<Metadata> {
  const { id } = await params;
  let hotel: HotelDetail;
  try { hotel = await hotelService.getHotel(id); } catch (error) { if (error instanceof ApiError && error.status === 404) notFound(); return { title: "Hotel details", description: "View hotel details and live room availability on Maharashtra Tourist Places.", robots: { index: false, follow: false } }; }
  const description = hotel.description?.slice(0, 155) || `View ${hotel.name} in ${hotel.city} and check live room availability.`;
  const image = hotel.cover_image_url ? [hotel.cover_image_url] : [];
  return { title: hotel.name, description, alternates: { canonical: `/hotels/${hotel.slug}` }, openGraph: { title: hotel.name, description, url: `/hotels/${hotel.slug}`, images: image }, twitter: { card: image.length ? "summary_large_image" : "summary", title: hotel.name, description, images: image } };
}

export default async function HotelPage({ params, searchParams }: PageProps<"/hotels/[id]">) {
  const { id } = await params; const search = parseHotelSearch(await searchParams);
  return <HotelDetailView key={`${id}-${JSON.stringify(search)}`} hotelRef={id} search={search} />;
}
