"use client";

import { useEffect } from "react";

export default function AdminError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    console.error("Maharashtra Tourist Places admin route failure", error.digest ?? error.name);
  }, [error]);

  return <main className="grid min-h-screen place-items-center bg-slate-100 px-6"><section className="panel max-w-lg text-center" role="alert"><p className="eyebrow text-red-600">Control center error</p><h1 className="page-title">This admin view could not be loaded</h1><p className="page-subtitle">No operation was submitted. Retry when the service is available.</p><button type="button" onClick={reset} className="btn-primary mt-6">Try again</button></section></main>;
}
