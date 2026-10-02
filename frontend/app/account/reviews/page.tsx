import type { Metadata } from "next";
import { ReviewList } from "@/src/components/account/ReviewList";
export const metadata: Metadata = { title: "Verified Stay Reviews" };
export default function ReviewsPage() { return <ReviewList />; }
