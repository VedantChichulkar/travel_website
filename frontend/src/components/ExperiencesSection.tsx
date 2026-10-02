import Link from "next/link";

import { SectionHeading } from "@/src/components/SectionHeading";
import { MAHARASHTRA_EXPERIENCES } from "@/src/data/maharashtra-experiences";

export function ExperiencesSection() {
  return (
    <section id="experiences" className="bg-white py-20">
      <div className="container-shell">
        <SectionHeading eyebrow="Ways to explore" title="Follow what draws you in" description="Six broad themes to help shape a Maharashtra journey. Detailed planning and availability remain with the relevant destination or operator." />
        <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {MAHARASHTRA_EXPERIENCES.map((experience) => (
            <Link href={`/experiences?category=${experience.slug}#explore-experiences`} key={experience.title} className="group rounded-2xl border border-[var(--line)] bg-white p-6 shadow-[var(--shadow-sm)] transition hover:border-slate-300">
              <span className="grid h-11 w-11 place-items-center rounded-xl bg-[var(--accent-soft)] text-[11px] font-black tracking-wider text-[var(--accent-strong)]" aria-hidden>{experience.marker}</span>
              <h3 className="mt-6 text-xl font-black tracking-tight text-[var(--brand)]">{experience.title}</h3>
              <p className="mt-3 text-sm leading-6 text-slate-600">{experience.description}</p>
              <span className="mt-5 inline-flex text-sm font-black text-[var(--accent)]">Explore theme <span aria-hidden className="ml-1 transition-transform group-hover:translate-x-1">→</span></span>
            </Link>
          ))}
        </div>
      </div>
    </section>
  );
}
