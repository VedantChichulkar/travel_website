import type { Metadata } from "next";
import { BookingDetail } from "@/src/components/account/BookingDetail";
export const metadata: Metadata = { title: "Booking Details" };
export default async function BookingDetailPage({ params }: { params: Promise<{ bookingReference: string }> }) { const { bookingReference } = await params; return <BookingDetail bookingReference={decodeURIComponent(bookingReference)} />; }
