import type { Metadata } from "next";

import { PartnerRouteGate } from "@/src/components/PartnerRouteGate";
import { PartnerPortalShell } from "@/src/components/PartnerPortalShell";

export const metadata: Metadata = {
  robots: { index: false, follow: false, nocache: true },
};

export default function PartnerLayout({ children }: { children: React.ReactNode }) {
  return <PartnerRouteGate><PartnerPortalShell>{children}</PartnerPortalShell></PartnerRouteGate>;
}
