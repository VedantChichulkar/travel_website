"use client";

import { DiscoveryErrorState } from "@/src/components/discovery/DiscoveryErrorState";

export default function InterestError({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return <DiscoveryErrorState reset={reset} title="We couldn’t load this interest" message="The Maharashtra discovery service is temporarily unavailable. Try again or continue through the district directory." />;
}

