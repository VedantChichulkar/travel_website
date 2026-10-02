import type { Metadata } from "next";

import { HotelResults } from "@/src/components/HotelResults";
import { parseHotelSearch } from "@/src/lib/hotel-search";

export const metadata: Metadata = {
  title: "Hotels in Maharashtra",
  description: "Search active Maharashtra Tourist Places hotels across Maharashtra using live destination, date, guest, and room availability filters.",
  alternates: { canonical: "/hotels" },
};

export default async function HotelsPage({ searchParams }: PageProps<"/hotels">) {
  const search = parseHotelSearch(await searchParams);
  return <HotelResults key={JSON.stringify(search)} search={search} />;
}
