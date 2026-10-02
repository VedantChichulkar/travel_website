"use client";

import { DiscoveryErrorState } from "@/src/components/discovery/DiscoveryErrorState";

export default function PlaceError({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return <DiscoveryErrorState reset={reset} title="We couldn’t load this place" message="The place record could not be loaded right now. Try again or continue through Maharashtra’s district directory." />;
}

