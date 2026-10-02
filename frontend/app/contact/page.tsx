import type { Metadata } from "next";
import { Suspense } from "react";

import { ContactPage } from "@/src/components/contact/ContactPage";

export const metadata: Metadata = {
  title: "Contact & Support",
  description: "Contact Maharashtra Tourist Places for hotel booking, Safari, cancellation, refund, partner, or general enquiries.",
  alternates: { canonical: "/contact" },
  openGraph: { title: "Contact & Support | Maharashtra Tourist Places", description: "Choose the right Maharashtra Tourist Places support path for your enquiry.", url: "/contact" },
};

export default function ContactRoute() {
  return <Suspense fallback={<div className="container-shell py-16"><div className="skeleton h-96 rounded-2xl" /></div>}><ContactPage /></Suspense>;
}
