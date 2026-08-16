import Link from "next/link";

export default function Home() {
  return (
    <section className="mx-auto flex w-full max-w-6xl flex-1 items-center px-4 py-20 sm:px-6">
      <div className="max-w-2xl">
        <p className="mb-4 text-sm font-semibold uppercase tracking-[0.2em] text-sky-700">Customer portal</p>
        <h1 className="text-4xl font-bold tracking-tight text-slate-950 sm:text-6xl">Your next journey starts here.</h1>
        <p className="mt-6 max-w-xl text-lg leading-8 text-slate-600">Create your customer account or sign in to manage your travel profile. Booking features are coming next.</p>
        <div className="mt-8 flex flex-wrap gap-3">
          <Link href="/register" className="rounded-lg bg-sky-700 px-5 py-3 font-semibold text-white hover:bg-sky-800">Create account</Link>
          <Link href="/login" className="rounded-lg border border-slate-300 bg-white px-5 py-3 font-semibold text-slate-800 hover:bg-slate-100">Sign in</Link>
        </div>
      </div>
    </section>
  );
}
