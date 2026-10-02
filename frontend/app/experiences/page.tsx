import type { Metadata } from "next";
import { Suspense } from "react";

import { ExperiencesExplorer } from "@/src/components/experiences/ExperiencesExplorer";

export const metadata: Metadata = {
  title: "Maharashtra Experiences & Culture",
  description: "Explore Maharashtra through heritage, wildlife, food, festivals, art, traditions, and the Konkan coast, then continue to canonical destinations, safaris, and stays.",
  alternates: { canonical: "/experiences" },
  openGraph: {
    title: "Maharashtra Experiences & Culture | Maharashtra Tourist Places",
    description: "A curated guide to Maharashtra experiences, culture, destinations, safaris, and stays.",
    url: "/experiences",
    images: [{ url: "/images/maharashtra-hero.png", alt: "Maharashtra landscape" }],
  },
};

export default function ExperiencesPage() {
  return <Suspense fallback={<div className="container-shell py-16" aria-label="Loading experiences"><div className="skeleton h-[32rem] rounded-2xl" /></div>}><ExperiencesExplorer /></Suspense>;
}
