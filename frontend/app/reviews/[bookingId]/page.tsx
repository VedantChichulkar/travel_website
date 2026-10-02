import { VerifiedStayReviewForm } from "@/src/components/VerifiedStayReviewForm";

export default async function ReviewPage({ params }: { params: Promise<{ bookingId: string }> }) {
  const { bookingId } = await params;
  return <VerifiedStayReviewForm bookingId={Number(bookingId)} />;
}
