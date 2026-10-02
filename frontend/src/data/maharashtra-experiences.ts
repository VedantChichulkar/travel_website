export type ExperienceCategorySlug =
  | "forts-heritage"
  | "wildlife-nature"
  | "food"
  | "festivals"
  | "art-traditions"
  | "beaches-coast";

export interface MaharashtraExperienceCategory {
  slug: ExperienceCategorySlug;
  title: string;
  marker: string;
  kicker: string;
  description: string;
}

export const MAHARASHTRA_EXPERIENCES: readonly MaharashtraExperienceCategory[] = [
  { slug: "forts-heritage", title: "Forts & Heritage", marker: "FH", kicker: "Stories in place", description: "Follow forts, historic precincts, caves, and architecture through the destinations that hold them." },
  { slug: "wildlife-nature", title: "Wildlife & Nature", marker: "WN", kicker: "Forests and landscapes", description: "Explore nature-led destinations, with managed safari requests kept in Maharashtra Tourist Places’ dedicated Safari flow." },
  { slug: "food", title: "Food", marker: "FD", kicker: "Regional kitchens", description: "Use Maharashtra’s regional cuisines as cultural context for deciding where to travel next." },
  { slug: "festivals", title: "Festivals", marker: "FE", kicker: "Shared traditions", description: "Read about enduring celebrations without relying on dates that may change from year to year." },
  { slug: "art-traditions", title: "Art & Traditions", marker: "AT", kicker: "Living culture", description: "Meet regional craft, performance, pilgrimage, and community traditions with respect for their context." },
  { slug: "beaches-coast", title: "Beaches & Coast", marker: "BC", kicker: "The Konkan edge", description: "Travel through coastal districts shaped by the Arabian Sea, local livelihoods, forts, and foodways." },
] as const;

export function isExperienceCategory(value: string | null): value is ExperienceCategorySlug {
  return MAHARASHTRA_EXPERIENCES.some((category) => category.slug === value);
}
