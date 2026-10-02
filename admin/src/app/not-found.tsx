import Link from "next/link";

export default function NotFound() {
  return <main className="grid min-h-screen place-items-center bg-slate-100 px-6"><section className="panel text-center"><p className="eyebrow">404</p><h1 className="page-title">Admin view not found</h1><Link href="/dashboard" className="btn-primary mt-6">Return to dashboard</Link></section></main>;
}
