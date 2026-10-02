import Link from "next/link";

export default function NotFound() {
  return <main className="grid min-h-[70vh] place-items-center px-6"><section className="text-center"><p className="eyebrow">404</p><h1 className="page-title">This Maharashtra Tourist Places page does not exist</h1><Link href="/" className="primary-button mt-6">Return home</Link></section></main>;
}
