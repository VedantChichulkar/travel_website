import Link from "next/link";

export interface BreadcrumbItem {
  label: string;
  href?: string;
}

export function Breadcrumbs({ items, tone = "light" }: { items: BreadcrumbItem[]; tone?: "light" | "dark" }) {
  return (
    <nav aria-label="Breadcrumb" className={tone === "dark" ? "text-white/75" : "text-slate-500"}>
      <ol className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs font-bold">
        {items.map((item, index) => (
          <li key={`${item.label}-${index}`} className="flex items-center gap-2">
            {index > 0 && <span aria-hidden className={tone === "dark" ? "text-white/35" : "text-slate-300"}>/</span>}
            {item.href ? <Link href={item.href} className="rounded-sm hover:underline">{item.label}</Link> : <span aria-current="page">{item.label}</span>}
          </li>
        ))}
      </ol>
    </nav>
  );
}

