import Image from "next/image";
import Link from "next/link";

export function RegionalHighlight() {
  return (
    <section className="container-shell pb-20">
      <div className="grid overflow-hidden rounded-[1.8rem] bg-[var(--brand-strong)] text-white shadow-[var(--shadow-lg)] lg:grid-cols-[1.05fr_.95fr]">
        <div className="p-7 sm:p-12 lg:p-14">
          <p className="eyebrow !text-[#ffc1a9]">Travel inspiration · Konkan</p>
          <h2 className="section-title mt-4 !text-white">Follow the coast where forts meet the sea.</h2>
          <p className="mt-5 max-w-xl text-base leading-7 text-slate-300">Begin at Raigad’s Maratha landmarks, continue through Ratnagiri’s temple shores, and slow down by the clear waters of Sindhudurg. The Konkan rewards unhurried travel.</p>
          <Link href="#search" className="primary-button mt-8">Explore Konkan stays <span aria-hidden>→</span></Link>
        </div>
        <div className="relative min-h-72 lg:min-h-full">
          <Image src="/images/destinations/sindhudurg.png" alt="Sindhudurg Fort surrounded by the blue waters of the Konkan coast" fill sizes="(min-width: 1024px) 45vw, 100vw" className="object-cover" />
        </div>
      </div>
    </section>
  );
}
