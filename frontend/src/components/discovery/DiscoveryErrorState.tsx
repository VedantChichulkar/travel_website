"use client";

import Link from "next/link";

export function DiscoveryErrorState({ reset, title, message }: { reset: () => void; title: string; message: string }) {
  return (
    <main className="container-shell py-20">
      <div className="surface-card mx-auto max-w-2xl p-8 text-center sm:p-12">
        <p className="eyebrow">Discovery unavailable</p>
        <h1 className="mt-3 text-3xl font-black tracking-tight text-[var(--brand)]">{title}</h1>
        <p className="mx-auto mt-4 max-w-xl text-sm leading-7 text-slate-600">{message}</p>
        <div className="mt-7 flex flex-wrap justify-center gap-3"><button type="button" onClick={reset} className="primary-button">Try again</button><Link href="/destinations" className="secondary-button">Browse destinations</Link></div>
      </div>
    </main>
  );
}

