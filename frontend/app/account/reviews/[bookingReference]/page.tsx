import type { Metadata } from "next";
import { ReviewByReference } from "@/src/components/account/ReviewByReference";
export const metadata: Metadata = { title: "Verified Stay Review" };
export default async function ReviewPage({ params }: { params: Promise<{ bookingReference: string }> }) { const { bookingReference } = await params; return <ReviewByReference bookingReference={decodeURIComponent(bookingReference)} />; }
