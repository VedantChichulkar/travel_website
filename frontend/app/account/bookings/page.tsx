import type { Metadata } from "next";
import { BookingList } from "@/src/components/account/BookingList";
export const metadata: Metadata = { title: "Hotel Bookings" };
export default function BookingsPage() { return <BookingList />; }
