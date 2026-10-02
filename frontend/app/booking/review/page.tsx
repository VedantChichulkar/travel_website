import { BookingReview } from "@/src/components/BookingReview";
import { parseHotelSearch } from "@/src/lib/hotel-search";

export default async function ReviewPage({ searchParams }: PageProps<"/booking/review">) {
  const raw = await searchParams; const hotelId = Number(Array.isArray(raw.hotelId) ? raw.hotelId[0] : raw.hotelId); const roomId = Number(Array.isArray(raw.roomId) ? raw.roomId[0] : raw.roomId); const search = parseHotelSearch(raw);
  if (!Number.isInteger(hotelId) || !Number.isInteger(roomId)) return <div className="container-shell py-16"><div className="surface-card p-10 text-center"><h1 className="text-2xl font-black text-[var(--brand-strong)]">Invalid room selection</h1><p className="mt-2 text-slate-500">Return to hotel search and select an available room.</p></div></div>;
  return <BookingReview key={`${hotelId}-${roomId}-${JSON.stringify(search)}`} hotelId={hotelId} roomId={roomId} search={search} />;
}
