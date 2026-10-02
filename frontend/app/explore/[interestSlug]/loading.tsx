export default function InterestLoading() {
  return <main aria-label="Loading interest discovery"><div className="skeleton h-[34rem] w-full" /><div className="container-shell py-16"><div className="skeleton h-4 w-40 rounded" /><div className="skeleton mt-4 h-10 w-72 max-w-full rounded" /><div className="mt-9 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">{Array.from({ length: 3 }, (_, index) => <div key={index} className="skeleton h-96 rounded-2xl" />)}</div></div></main>;
}

