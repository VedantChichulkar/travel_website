export default function DestinationsLoading() {
  return <main className="container-shell py-14" aria-label="Loading destination page"><div className="skeleton h-10 w-72 rounded-lg" /><div className="skeleton mt-4 h-5 w-full max-w-xl rounded" /><div className="mt-12 grid gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">{Array.from({ length: 8 }, (_, index) => <div key={index} className="skeleton h-80 rounded-2xl" />)}</div></main>;
}
