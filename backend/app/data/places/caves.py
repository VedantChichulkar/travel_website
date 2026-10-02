"""Reviewed cave and rock-cut heritage records."""

from datetime import date

from app.data.places.types import CuratedPlace, SourceProvenance
from app.models.place import SpiritualTradition


VERIFIED_ON = date(2026, 9, 25)


def source(name: str, url: str) -> tuple[SourceProvenance, ...]:
    return (SourceProvenance(name, url, VERIFIED_ON),)


CAVE_PLACES: tuple[CuratedPlace, ...] = (
    CuratedPlace(
        name="Ajanta Caves",
        district_slug="chhatrapati-sambhajinagar",
        short_description="A UNESCO-listed group of Buddhist rock-cut monuments known for surviving paintings and sculpture.",
        description="Ajanta Caves form a horseshoe-shaped complex of Buddhist monuments excavated in two broad phases from the second century BCE. Its monasteries and worship halls preserve important examples of Buddhist painting, sculpture and rock-cut architecture. UNESCO inscribed Ajanta on the World Heritage List in 1983.",
        interest_slugs=("ancient-caves", "history-architecture", "sacred-spiritual"),
        spiritual_tradition=SpiritualTradition.BUDDHIST,
        is_featured=True,
        display_order=10,
        sources=source("UNESCO World Heritage Centre", "https://whc.unesco.org/en/list/242"),
    ),
    CuratedPlace(
        name="Ellora Caves",
        district_slug="chhatrapati-sambhajinagar",
        short_description="A UNESCO-listed rock-cut complex containing Buddhist, Hindu and Jain monuments.",
        description="Ellora Caves comprise 34 Buddhist, Hindu and Jain monuments cut into a basalt escarpment between the sixth and tenth centuries. The complex includes monasteries, temples and the monolithic Kailasa temple, reflecting several religious and artistic traditions at one site. UNESCO inscribed Ellora on the World Heritage List in 1983.",
        interest_slugs=("ancient-caves", "history-architecture", "sacred-spiritual"),
        spiritual_tradition=SpiritualTradition.MULTI_TRADITION,
        is_featured=True,
        display_order=20,
        sources=source("UNESCO World Heritage Centre", "https://whc.unesco.org/en/list/243"),
    ),
    CuratedPlace(
        name="Elephanta Caves",
        district_slug="raigad",
        short_description="A UNESCO-listed cave complex on Elephanta Island centred on monumental sculptures associated with Shiva.",
        description="Elephanta Caves occupy Elephanta Island, also known as Gharapuri, in Mumbai Harbour. The principal cave contains large rock-cut reliefs associated with the worship of Shiva, while the wider property preserves a significant ensemble of early medieval Indian art. UNESCO inscribed the caves on the World Heritage List in 1987.",
        interest_slugs=("ancient-caves", "history-architecture", "sacred-spiritual"),
        spiritual_tradition=SpiritualTradition.HINDU,
        is_featured=True,
        display_order=30,
        sources=source("UNESCO World Heritage Centre", "https://whc.unesco.org/en/list/244"),
    ),
    CuratedPlace(
        name="Karla Caves",
        district_slug="pune",
        short_description="An ancient Buddhist rock-cut complex near Lonavala with a prominent chaitya hall.",
        description="Karla Caves are a group of Buddhist rock-cut monuments near Lonavala in Pune district. The complex includes monastic spaces and a large chaitya, or worship hall, whose columns and carved façade illustrate the development of early western Indian cave architecture.",
        interest_slugs=("ancient-caves", "history-architecture"),
        spiritual_tradition=SpiritualTradition.BUDDHIST,
        display_order=40,
        sources=source("Department of Tourism, Government of Maharashtra", "https://maharashtratourism.gov.in/tourist-intrests/caves/"),
    ),
    CuratedPlace(
        name="Bhaja Caves",
        district_slug="pune",
        short_description="An early Buddhist rock-cut complex near Lonavala containing a chaitya hall, viharas and stupas.",
        description="Bhaja Caves are an early group of Buddhist rock-cut monuments in Pune district. Their chaitya hall, monastic residences and group of stupas document the architectural and religious use of the site, which lies close to the historic route through the Western Ghats.",
        interest_slugs=("ancient-caves", "history-architecture"),
        spiritual_tradition=SpiritualTradition.BUDDHIST,
        display_order=50,
        sources=source("Department of Tourism, Government of Maharashtra", "https://maharashtratourism.gov.in/cave/bhaja/"),
    ),
    CuratedPlace(
        name="Kanheri Caves",
        district_slug="mumbai-suburban",
        short_description="A large Buddhist rock-cut monastic complex within Sanjay Gandhi National Park.",
        description="Kanheri Caves are a group of more than one hundred excavations within Sanjay Gandhi National Park in Mumbai. Developed over many centuries, the site includes monastic cells, prayer halls, stupas, sculptures, inscriptions and rock-cut water systems associated with a major Buddhist centre.",
        interest_slugs=("ancient-caves", "history-architecture"),
        spiritual_tradition=SpiritualTradition.BUDDHIST,
        display_order=60,
        sources=source("Department of Tourism, Government of Maharashtra", "https://maharashtratourism.gov.in/cave/kanheri/"),
    ),
)

