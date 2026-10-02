import Image from "next/image";
import { HotelSearchForm } from "@/src/components/HotelSearchForm";

export function Hero() {
  return (
    <section className="relative isolate min-h-[760px] overflow-hidden bg-[var(--brand)] text-white sm:min-h-[800px]">
      <Image src="/images/maharashtra-hero.png" alt="A Sahyadri hill fort overlooking the Konkan coast at sunrise" fill priority sizes="100vw" className="object-cover object-[68%_center]" />
      <div className="absolute inset-0 bg-[rgba(9,31,49,.72)] sm:bg-[linear-gradient(90deg,rgba(9,31,49,.94)_0%,rgba(9,31,49,.76)_48%,rgba(9,31,49,.2)_88%)]" />
      <div className="container-shell relative flex min-h-[760px] items-center py-16 sm:min-h-[800px] sm:py-24">
        <div className="w-full">
          <div className="max-w-3xl">
            <p className="eyebrow !text-[var(--accent-on-dark)]">Maharashtra, thoughtfully explored</p>
            <h1 className="display-title mt-5 text-balance !text-white">Discover Maharashtra, Your Way.</h1>
            <p className="mt-7 max-w-2xl text-lg leading-8 text-slate-100 sm:text-xl">Find stays and travel ideas across vibrant cities, the Sahyadri hills, forest country, heritage landscapes, and the Konkan coast.</p>
          </div>
          <div className="mt-10 w-full"><HotelSearchForm hero /></div>
          <p className="mt-6 text-sm font-semibold text-stone-200">Search live Maharashtra Tourist Places destinations, choose your dates, and compare available stays.</p>
        </div>
      </div>
    </section>
  );
}
