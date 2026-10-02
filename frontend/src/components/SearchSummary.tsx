import type { HotelSearchParams } from "@/src/types/hotel";

function formatDate(value: string, includeYear = false): string {
  const [year, month, day] = value.split("-").map(Number);
  if (!year || !month || !day) return value;
  return new Intl.DateTimeFormat("en-IN", { day: "numeric", month: "short", year: includeYear ? "numeric" : undefined }).format(new Date(year, month - 1, day));
}

export function SearchSummary({ search, modifyOpen, onToggle }: { search: HotelSearchParams; modifyOpen: boolean; onToggle: () => void }) {
  const roomLabel = `${search.rooms} room${search.rooms === 1 ? "" : "s"}`;
  const dateLabel = search.checkIn && search.checkOut ? `${formatDate(search.checkIn)} – ${formatDate(search.checkOut, true)}` : "Dates not selected";

  return (
    <div className="flex flex-col justify-between gap-6 sm:flex-row sm:items-end">
      <div>
        <p className="eyebrow">Maharashtra stays</p>
        <h1 className="page-title mt-3">Hotels in {search.city || "your destination"}</h1>
        <p className="mt-4 flex flex-wrap items-center gap-x-2 gap-y-1 text-sm font-semibold text-slate-600 sm:text-base">
          <span>{dateLabel}</span><span aria-hidden className="text-slate-300">·</span><span>{search.adults} adult{search.adults === 1 ? "" : "s"}</span><span aria-hidden className="text-slate-300">·</span><span>{search.children} child{search.children === 1 ? "" : "ren"}</span><span aria-hidden className="text-slate-300">·</span><span>{roomLabel}</span>
        </p>
      </div>
      <button type="button" onClick={onToggle} aria-expanded={modifyOpen} aria-controls="modify-search" className="secondary-button shrink-0 self-start sm:self-auto">{modifyOpen ? "Hide search" : "Modify search"}</button>
    </div>
  );
}
