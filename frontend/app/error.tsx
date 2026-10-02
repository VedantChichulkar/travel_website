"use client";

import { useEffect } from "react";

export default function GlobalError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    console.error("Maharashtra Tourist Places route failure", error.digest ?? error.name);
  }, [error]);

  return (
    <main className="grid min-h-[70vh] place-items-center px-6">
      <section className="max-w-lg rounded-3xl border border-red-100 bg-white p-8 text-center shadow-sm" role="alert">
        <p className="text-xs font-black uppercase tracking-[.16em] text-red-600">Something went wrong</p>
        <h1 className="mt-3 text-2xl font-black text-[#0b163d]">We could not load this page</h1>
        <p className="mt-3 text-sm text-slate-600">Your data was not changed. Try the request again.</p>
        <button type="button" onClick={reset} className="primary-button mt-6">Try again</button>
      </section>
    </main>
  );
}
