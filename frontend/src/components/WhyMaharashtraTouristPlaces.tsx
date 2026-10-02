import { SectionHeading } from "@/src/components/SectionHeading";

const REASONS = [
  { title: "Maharashtra-first discovery", description: "Districts, destinations, stays, and safari listings come together in one regional travel platform." },
  { title: "Live stay search", description: "Search the active hotel catalogue by destination, dates, guests, and rooms before choosing a stay." },
  { title: "Partner verification process", description: "Hotel partners can submit business and property details for administrative review; approval is never implied by payment." },
  { title: "Joined-up trip management", description: "Signed-in travellers can manage supported bookings, safari requests, notifications, and messages from their account." },
];

export function WhyMaharashtraTouristPlaces() {
  return (
    <section id="why-maharashtra-tourist-places" className="container-shell py-20">
      <SectionHeading eyebrow="Why Maharashtra Tourist Places" title="Built for a clearer Maharashtra journey" description="Practical travel discovery and account tools, with transparent review and availability workflows." align="center" />
      <div className="mt-10 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
        {REASONS.map((reason, index) => <article key={reason.title} className="surface-card p-6"><span className="grid h-9 w-9 place-items-center rounded-lg bg-[var(--accent-soft)] text-xs font-black text-[var(--accent-strong)]">0{index + 1}</span><h3 className="mt-6 text-lg font-black text-[var(--brand)]">{reason.title}</h3><p className="mt-3 text-sm leading-6 text-slate-600">{reason.description}</p></article>)}
      </div>
    </section>
  );
}
