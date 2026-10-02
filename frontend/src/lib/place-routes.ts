export function placePath(districtSlug: string, placeSlug: string) {
  return `/places/${encodeURIComponent(districtSlug)}/${encodeURIComponent(placeSlug)}`;
}

export function interestPath(interestSlug: string) {
  return `/explore/${encodeURIComponent(interestSlug)}`;
}

export function placeStayPath({
  districtSlug,
  districtName,
  destinationSlug,
  destinationName,
}: {
  districtSlug: string;
  districtName: string;
  destinationSlug?: string;
  destinationName?: string;
}) {
  const destination = destinationSlug ? `${districtSlug}/${destinationSlug}` : districtSlug;
  const query = new URLSearchParams({
    destination,
    city: destinationName || districtName,
  });
  return `/hotels?${query.toString()}`;
}
