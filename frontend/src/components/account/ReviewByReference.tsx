"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { VerifiedStayReviewForm } from "@/src/components/VerifiedStayReviewForm";
import { bookingService } from "@/src/services/booking.service";

export function ReviewByReference({ bookingReference }: { bookingReference: string }) { const [id, setId] = useState<number>(); const [error, setError] = useState(""); useEffect(() => { let active = true; void bookingService.listMine().then((result) => { const booking = result.items.find((item) => item.booking_reference === bookingReference); if (!booking) throw new Error("Booking not found"); if (active) setId(booking.id); }).catch((cause) => active && setError(cause instanceof Error ? cause.message : "Review could not be loaded.")); return () => { active = false; }; }, [bookingReference]); if (error) return <div role="alert" className="content-card text-center text-red-700">{error}<Link href="/account/reviews" className="secondary-button mt-5">Back to reviews</Link></div>; if (!id) return <div className="skeleton h-80 rounded-2xl" />; return <VerifiedStayReviewForm bookingId={id} embedded />; }
