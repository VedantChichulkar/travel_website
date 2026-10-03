import type { Metadata } from "next";
import Link from "next/link";

import { DestinationPreview } from "@/src/components/DestinationPreview";
import { InterestsSection } from "@/src/components/InterestsSection";
import { FeaturedHotels } from "@/src/components/FeaturedHotels";
import { Hero } from "@/src/components/Hero";
import { SafariTeaser } from "@/src/components/SafariTeaser";
import { SectionHeading } from "@/src/components/SectionHeading";
import { SponsoredRotator } from "@/src/components/SponsoredRotator";
import { WhyMaharashtraTouristPlaces } from "@/src/components/WhyMaharashtraTouristPlaces";

export const metadata: Metadata = {
  title: "Discover Maharashtra, Your Way",
  description: "Explore Maharashtra destinations, search active hotels, and discover supported jungle safari experiences with Maharashtra Tourist Places.",
  alternates: { canonical: "/" },
};

export default function Home() {
  return (
    <>
      <Hero />
      <section id="destinations" className="container-shell py-20">
        <div className="flex flex-col justify-between gap-6 sm:flex-row sm:items-end">
          <SectionHeading eyebrow="Explore Maharashtra" title="Districts with stories of their own" description="Start with live destination data, then follow the landscape, local context, and available places to stay." />
          <Link href="/destinations" className="secondary-button shrink-0">Explore all Maharashtra <span aria-hidden className="ml-2">→</span></Link>
        </div>
        <div className="mt-9"><DestinationPreview /></div>
      </section>
      <section className="border-b border-[var(--line)] bg-[var(--surface-muted)] py-20">
        <div className="container-shell">
          <div className="flex flex-col justify-between gap-6 sm:flex-row sm:items-end"><SectionHeading eyebrow="Jungle safaris" title="Begin with the forest" description="Explore active safari listings and send an availability request. Availability, pricing, and external booking confirmation follow the safari workflow." /><Link href="/safaris" className="secondary-button shrink-0">Explore safaris <span aria-hidden className="ml-2">→</span></Link></div>
          <div className="mt-10"><SafariTeaser /></div>
        </div>
      </section>
      <SponsoredRotator placement="HOMEPAGE_BANNER" />
      <section className="border-b border-[var(--line)] bg-white py-20">
        <div className="container-shell">
          <div className="flex flex-col justify-between gap-6 sm:flex-row sm:items-end"><SectionHeading eyebrow="Discover stays" title="A considered place to pause" description="Browse active properties from the Maharashtra Tourist Places catalogue. Starting prices and availability depend on your selected dates." /><Link href="/hotels" className="secondary-button shrink-0">View all hotels <span aria-hidden className="ml-2">→</span></Link></div>
          <div className="mt-9"><FeaturedHotels /></div>
        </div>
      </section>
      <InterestsSection />
      <WhyMaharashtraTouristPlaces />
    </>
  );
}
