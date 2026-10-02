"use client";

import { useEffect, useState } from "react";

import { DistrictCard } from "@/src/components/destinations/DistrictCard";
import { MAHARASHTRA_DESTINATIONS } from "@/src/data/maharashtra-destinations";
import { destinationService } from "@/src/services/destination.service";
import type { PublicDistrict } from "@/src/types/destination";

export function DestinationPreview() {
  const [districts, setDistricts] = useState<PublicDistrict[] | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let active = true;
    void destinationService.listDistricts().then((response) => {
      if (!active) return;
      const bySlug = new Map(response.items.map((district) => [district.slug, district]));
      const curated = MAHARASHTRA_DESTINATIONS
        .map((destination) => bySlug.get(destination.districtSlug))
        .filter((district): district is PublicDistrict => Boolean(district))
        .filter((district, index, items) => items.findIndex((item) => item.slug === district.slug) === index)
        .slice(0, 4);
      setDistricts(curated.length ? curated : response.items.slice(0, 4));
    }).catch(() => { if (active) setFailed(true); });
    return () => { active = false; };
  }, []);

  if (!districts && !failed) return <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">{Array.from({ length: 4 }, (_, index) => <div key={index} className="skeleton h-80 rounded-[1.4rem]" />)}</div>;
  if (failed) return <State title="Destinations are taking a little longer to load." detail="You can still search for a district or place above." />;
  if (!districts?.length) return <State title="No destinations are available right now." detail="Please check again soon." />;

  return <div className="grid auto-rows-fr gap-5 sm:grid-cols-2 lg:grid-cols-4">{districts.map((district) => <DistrictCard key={district.slug} district={district} />)}</div>;
}

function State({ title, detail }: { title: string; detail: string }) {
  return <div className="surface-card p-8 text-center"><p className="font-bold text-[var(--brand)]">{title}</p><p className="mt-2 text-sm text-slate-500">{detail}</p></div>;
}
