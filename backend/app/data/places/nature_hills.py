"""Reviewed nature and hill Place records."""

from datetime import date

from app.data.places.types import CuratedPlace, SourceProvenance


VERIFIED_ON = date(2026, 9, 27)


def source(name: str, url: str) -> tuple[SourceProvenance, ...]:
    return (SourceProvenance(name, url, VERIFIED_ON),)


MAHARASHTRA_TOURISM = "Department of Tourism, Government of Maharashtra"


NATURE_HILL_PLACES: tuple[CuratedPlace, ...] = (
    CuratedPlace(
        name="Mahabaleshwar Hill Station",
        district_slug="satara",
        short_description="A Sahyadri hill station shaped by forested valleys, lakes and high viewpoints.",
        description="Mahabaleshwar occupies a high plateau in the Western Ghats of Satara district. Its wooded slopes, valley viewpoints and Venna Lake form a connected hill landscape that has long supported recreation and travel in the Sahyadri range.",
        interest_slugs=("nature-hills",),
        is_featured=True,
        display_order=10,
        sources=source(MAHARASHTRA_TOURISM, "https://maharashtratourism.gov.in/tourist-intrests/hill-stations/"),
    ),
    CuratedPlace(
        name="Panchgani Table Land",
        district_slug="satara",
        short_description="A broad laterite plateau above Panchgani with views across the surrounding valleys.",
        description="Table Land is the elevated, level laterite plateau associated with Panchgani in Satara district. Its open surface and plateau edge provide wide views over the Krishna valley and the folded terrain of the surrounding Sahyadri hills.",
        interest_slugs=("nature-hills",),
        display_order=20,
        sources=source(MAHARASHTRA_TOURISM, "https://maharashtratourism.gov.in/nature/panchgani/"),
    ),
    CuratedPlace(
        name="Matheran Hill Station",
        district_slug="raigad",
        short_description="A forested hill station in Raigad with walking routes and viewpoints over the Western Ghats.",
        description="Matheran is a compact hill station on a forested plateau in Raigad district. Paths connect its settlement, lake and viewpoints, which overlook steep valleys and neighbouring ridges of the Western Ghats.",
        interest_slugs=("nature-hills",),
        is_featured=True,
        display_order=30,
        sources=source(MAHARASHTRA_TOURISM, "https://maharashtratourism.gov.in/nature/matheran/"),
    ),
    CuratedPlace(
        name="Lonavala Hill Station",
        district_slug="pune",
        short_description="A Western Ghats hill station surrounded by ridges, lakes and seasonal watercourses.",
        description="Lonavala lies in the Bhor Ghat section of the Western Ghats in Pune district. The surrounding landscape combines escarpments, wooded valleys, reservoirs and historic routes between the Konkan coast and the Deccan plateau.",
        interest_slugs=("nature-hills",),
        display_order=40,
        sources=source(MAHARASHTRA_TOURISM, "https://maharashtratourism.gov.in/nature/lonavala/"),
    ),
    CuratedPlace(
        name="Khandala Ghat",
        district_slug="pune",
        short_description="A mountain-pass landscape where the Bhor Ghat descends through the Western Ghats.",
        description="Khandala occupies the escarpment of the Bhor Ghat in Pune district. Its ridges and valleys mark a major natural passage between the Deccan plateau and the Konkan lowlands, alongside long-established road and rail approaches.",
        interest_slugs=("nature-hills",),
        display_order=50,
        sources=source(MAHARASHTRA_TOURISM, "https://maharashtratourism.gov.in/tourist-intrests/hill-stations/"),
    ),
    CuratedPlace(
        name="Chikhaldara Hill Station",
        district_slug="amravati",
        short_description="A forested Satpura hill station overlooking valleys in northern Amravati district.",
        description="Chikhaldara sits in the Satpura highlands of Amravati district. Forested slopes, lakes and valley viewpoints define the hill landscape, which lies near the wider protected forests of Melghat.",
        interest_slugs=("nature-hills",),
        is_featured=True,
        display_order=60,
        sources=source(MAHARASHTRA_TOURISM, "https://maharashtratourism.gov.in/tourist-intrests/hill-stations/"),
    ),
    CuratedPlace(
        name="Bhandardara Lake and Dam",
        district_slug="ahilyanagar",
        short_description="A reservoir landscape formed by Wilson Dam on the Pravara River in the Sahyadri hills.",
        description="Bhandardara Lake, also called Arthur Lake, is the reservoir formed by Wilson Dam on the Pravara River in Ahilyanagar district. The water body sits among the high ridges and valleys of the northern Sahyadri range.",
        interest_slugs=("nature-hills",),
        display_order=70,
        sources=source("Ahilyanagar District, Government of Maharashtra", "https://ahmednagar.nic.in/en/tourist-place/bhandardara/"),
    ),
    CuratedPlace(
        name="Igatpuri Hill Station",
        district_slug="nashik",
        short_description="A Western Ghats hill station set among forested ridges and valleys in Nashik district.",
        description="Igatpuri lies in the Western Ghats of Nashik district near an important pass between the Konkan and the Deccan plateau. Its setting is defined by steep ridges, valley landscapes and dense vegetation around the town.",
        interest_slugs=("nature-hills",),
        display_order=80,
        sources=source(MAHARASHTRA_TOURISM, "https://maharashtratourism.gov.in/nature/igatpuri/"),
    ),
    CuratedPlace(
        name="Amboli Hill Station",
        district_slug="sindhudurg",
        short_description="A high-rainfall Western Ghats landscape with forest, waterfalls and rich biodiversity.",
        description="Amboli lies in the Western Ghats above Sawantwadi in Sindhudurg district. Forested slopes, streams and waterfalls shape the hill landscape, while the surrounding Amboli forest supports notable biological diversity.",
        interest_slugs=("nature-hills",),
        is_featured=True,
        display_order=90,
        sources=source("Sindhudurg District, Government of Maharashtra", "https://sindhudurg.nic.in/en/tourist-place/amboli_en/"),
    ),
    CuratedPlace(
        name="Kaas Plateau",
        district_slug="satara",
        short_description="A lateritic wildflower plateau forming a component of the UNESCO-listed Western Ghats property.",
        description="Kaas Plateau is a lateritic plateau near Satara known for its seasonally changing plant communities and high biological diversity. It is component 36 of the Sahyadri sub-cluster within the serial Western Ghats World Heritage property, inscribed by UNESCO in 2012.",
        interest_slugs=("nature-hills",),
        is_featured=True,
        display_order=100,
        sources=(
            SourceProvenance(MAHARASHTRA_TOURISM, "https://maharashtratourism.gov.in/nature/kaas-plateau/", VERIFIED_ON),
            SourceProvenance("UNESCO World Heritage Centre", "https://whc.unesco.org/en/list/1342", VERIFIED_ON),
        ),
    ),
)
