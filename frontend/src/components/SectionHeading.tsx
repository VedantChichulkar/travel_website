export function SectionHeading({ eyebrow, title, description, align = "left", tone = "default" }: { eyebrow: string; title: string; description?: string; align?: "left" | "center"; tone?: "default" | "inverse" }) {
  const inverse = tone === "inverse";
  return <div className={align === "center" ? "mx-auto max-w-2xl text-center" : "max-w-2xl"}><p className={`eyebrow ${inverse ? "!text-[var(--accent-on-dark)]" : ""}`}>{eyebrow}</p><h2 className={`section-title mt-3 text-balance ${inverse ? "!text-white" : ""}`}>{title}</h2>{description && <p className={`body-lead mt-4 ${inverse ? "!text-slate-300" : ""}`}>{description}</p>}</div>;
}
