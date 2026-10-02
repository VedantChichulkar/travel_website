import type { ExperienceCategorySlug } from "@/src/data/maharashtra-experiences";

export interface MaharashtraDestination {
  city: string;
  districtSlug: string;
  code: string;
  region: string;
  descriptor: string;
  experience: string;
  attractions: readonly string[];
  image: string;
  imageAlt: string;
  categories: readonly ExperienceCategorySlug[];
}

export const MAHARASHTRA_DESTINATIONS: readonly MaharashtraDestination[] = [
  { city: "Mumbai", districtSlug: "mumbai-city", code: "MMR", region: "Konkan", descriptor: "Heritage, coastline & city life", experience: "Urban heritage", attractions: ["Gateway of India", "Marine Drive", "Elephanta Caves"], image: "/images/destinations/mumbai.png", imageAlt: "Gateway of India and the Mumbai coastline", categories: ["forts-heritage", "festivals", "beaches-coast"] },
  { city: "Pune", districtSlug: "pune", code: "PNQ", region: "Western Maharashtra", descriptor: "Wadas, forts & cultural trails", experience: "Living heritage", attractions: ["Shaniwar Wada", "Sinhagad Fort", "Aga Khan Palace"], image: "/images/destinations/pune.png", imageAlt: "Shaniwar Wada and traditional Pune architecture", categories: ["forts-heritage", "food", "art-traditions"] },
  { city: "Nagpur", districtSlug: "nagpur", code: "NAG", region: "Vidarbha", descriptor: "Wildlife gateways & Vidarbha culture", experience: "Nature & culture", attractions: ["Deekshabhoomi", "Futala Lake", "Wildlife gateways"], image: "/images/destinations/nagpur.png", imageAlt: "Deekshabhoomi amid the Vidarbha landscape in Nagpur", categories: ["wildlife-nature", "food", "art-traditions"] },
  { city: "Nashik", districtSlug: "nashik", code: "NSK", region: "North Maharashtra", descriptor: "Pilgrimage, vineyards & ancient caves", experience: "Spiritual journeys", attractions: ["Trimbakeshwar", "Godavari Ghats", "Vineyard country"], image: "/images/destinations/nashik.png", imageAlt: "Trimbakeshwar temple and Godavari ghats near Nashik", categories: ["forts-heritage", "art-traditions"] },
  { city: "Chhatrapati Sambhajinagar", districtSlug: "chhatrapati-sambhajinagar", code: "IXU", region: "Marathwada", descriptor: "World heritage & Deccan history", experience: "World heritage", attractions: ["Ajanta Caves", "Ellora Caves", "Daulatabad Fort"], image: "/images/destinations/chhatrapati-sambhajinagar.png", imageAlt: "Ellora's rock-cut heritage near Chhatrapati Sambhajinagar", categories: ["forts-heritage", "art-traditions"] },
  { city: "Kolhapur", districtSlug: "kolhapur", code: "KLH", region: "Western Maharashtra", descriptor: "Temples, forts & bold regional traditions", experience: "Sacred heritage", attractions: ["Mahalaxmi Temple", "Panhala Fort", "Rankala Lake"], image: "/images/destinations/kolhapur.png", imageAlt: "Mahalaxmi Temple and Panhala heritage in Kolhapur", categories: ["forts-heritage", "food", "art-traditions"] },
  { city: "Pandharpur", districtSlug: "solapur", code: "SOL", region: "Western Maharashtra", descriptor: "Vitthal devotion & the timeless Wari", experience: "Spiritual Maharashtra", attractions: ["Vitthal-Rukmini Temple", "Chandrabhaga River"], image: "/images/destinations/pandharpur.png", imageAlt: "Wari pilgrims approaching Vitthal-Rukmini Temple beside the Chandrabhaga River in Pandharpur", categories: ["festivals", "art-traditions"] },
  { city: "Ratnagiri", districtSlug: "ratnagiri", code: "RTC", region: "Konkan", descriptor: "Konkan shores & coastal heritage", experience: "Coastal journeys", attractions: ["Ganpatipule", "Ratnadurg Fort", "Konkan coastline"], image: "/images/destinations/ratnagiri.png", imageAlt: "Ganpatipule coast and Ratnagiri's coconut-lined Konkan landscape", categories: ["forts-heritage", "food", "beaches-coast"] },
  { city: "Raigad", districtSlug: "raigad", code: "RIG", region: "Konkan", descriptor: "Maratha forts & Arabian Sea escapes", experience: "Forts & coast", attractions: ["Raigad Fort", "Alibaug", "Murud-Janjira"], image: "/images/destinations/raigad.png", imageAlt: "Raigad Fort rising above the Sahyadri landscape", categories: ["forts-heritage", "beaches-coast"] },
  { city: "Sindhudurg", districtSlug: "sindhudurg", code: "SDG", region: "South Konkan", descriptor: "Clear waters & coastal heritage", experience: "Konkan coast", attractions: ["Tarkarli", "Sindhudurg Fort", "Malvan"], image: "/images/destinations/sindhudurg.png", imageAlt: "Sindhudurg Fort surrounded by clear Konkan coastal waters", categories: ["forts-heritage", "food", "beaches-coast"] },
] as const;

export const MAHARASHTRA_DESTINATION_NAMES = MAHARASHTRA_DESTINATIONS.map((destination) => destination.city);

export function curatedDestinationForDistrict(districtSlug: string): MaharashtraDestination | undefined {
  return MAHARASHTRA_DESTINATIONS.find((destination) => destination.districtSlug === districtSlug);
}
