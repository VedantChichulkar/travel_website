"""Reviewed multi-faith sacred and spiritual Place records."""

from datetime import date

from app.data.places.types import CuratedPlace, SourceProvenance
from app.models.place import SpiritualTradition


VERIFIED_ON = date(2026, 9, 25)


def source(name: str, url: str) -> tuple[SourceProvenance, ...]:
    return (SourceProvenance(name, url, VERIFIED_ON),)


SACRED_SPIRITUAL_PLACES: tuple[CuratedPlace, ...] = (
    CuratedPlace(
        name="Shri Vitthal-Rukmini Temple, Pandharpur",
        slug="shri-vitthal-rukmini-temple",
        district_slug="solapur",
        short_description="A major Hindu pilgrimage temple at Pandharpur dedicated to Vitthal and Rukmini.",
        description="Shri Vitthal-Rukmini Temple stands at the centre of the pilgrimage town of Pandharpur in Solapur district. Dedicated to Vitthal and Rukmini, it is closely associated with Maharashtra's Varkari tradition and receives large pilgrim gatherings during Ashadhi and Kartiki Ekadashi.",
        interest_slugs=("sacred-spiritual",),
        spiritual_tradition=SpiritualTradition.HINDU,
        is_featured=True,
        display_order=10,
        sources=source("Solapur District, Government of Maharashtra", "https://solapur.gov.in/en/tourist-place/pandharpur/"),
    ),
    CuratedPlace(
        name="Trimbakeshwar Temple",
        district_slug="nashik",
        short_description="A historic Shiva temple and pilgrimage centre in Trimbak, west of Nashik.",
        description="Trimbakeshwar Temple is a Hindu pilgrimage centre in the town of Trimbak, near the Brahmagiri hills in Nashik district. The present stone temple is associated with the Jyotirlinga tradition, and the wider sacred landscape is linked with the source region of the Godavari River.",
        interest_slugs=("sacred-spiritual", "history-architecture"),
        spiritual_tradition=SpiritualTradition.HINDU,
        display_order=20,
        sources=source("Nashik District, Government of Maharashtra", "https://nashik.gov.in/en/tourist-place/trimbakeshwar-temple/"),
    ),
    CuratedPlace(
        name="Ghrishneshwar Temple",
        district_slug="chhatrapati-sambhajinagar",
        short_description="A historic Shiva temple at Verul near the Ellora Caves.",
        description="Ghrishneshwar Temple stands at Verul close to the Ellora Caves in Chhatrapati Sambhajinagar district. The active Hindu temple is associated with the Jyotirlinga tradition, and its present stone form reflects rebuilding and patronage over several periods.",
        interest_slugs=("sacred-spiritual", "history-architecture"),
        spiritual_tradition=SpiritualTradition.HINDU,
        display_order=30,
        sources=source("Department of Tourism, Government of Maharashtra", "https://maharashtratourism.gov.in/temple/ghrishneshwar/"),
    ),
    CuratedPlace(
        name="Tulja Bhavani Temple",
        district_slug="dharashiv",
        short_description="A prominent Hindu pilgrimage temple dedicated to Bhavani in Tuljapur.",
        description="Tulja Bhavani Temple is an active Hindu pilgrimage site in Tuljapur, Dharashiv district. The hill-set temple complex is dedicated to the goddess Bhavani and has longstanding importance in Maharashtra's religious history.",
        interest_slugs=("sacred-spiritual",),
        spiritual_tradition=SpiritualTradition.HINDU,
        display_order=40,
        sources=source("Department of Tourism, Government of Maharashtra", "https://maharashtratourism.gov.in/temple/tuljapur/"),
    ),
    CuratedPlace(
        name="Shree Siddhivinayak Ganapati Temple",
        district_slug="mumbai-city",
        short_description="An active Ganapati temple established at Prabhadevi in Mumbai in 1801.",
        description="Shree Siddhivinayak Ganapati Temple is an active Hindu shrine at Prabhadevi in Mumbai. The original temple was established in 1801, while the present complex developed around the historic core and is administered by a trust governed under Maharashtra law.",
        interest_slugs=("sacred-spiritual", "history-architecture"),
        spiritual_tradition=SpiritualTradition.HINDU,
        display_order=50,
        sources=source("Mumbai City District, Government of Maharashtra", "https://mumbaicity.gov.in/en/tourist-place/siddhivinayak-temple/"),
    ),
    CuratedPlace(
        name="Deekshabhoomi",
        district_slug="nagpur",
        short_description="A Buddhist monument in Nagpur marking Dr. B. R. Ambedkar's public conversion to Buddhism in 1956.",
        description="Deekshabhoomi is a Buddhist pilgrimage and memorial site in Nagpur. It marks the place where Dr. B. R. Ambedkar embraced Buddhism with a large gathering of followers on 14 October 1956, and its modern stupa has become a major landmark of the city.",
        interest_slugs=("sacred-spiritual", "history-architecture"),
        spiritual_tradition=SpiritualTradition.BUDDHIST,
        is_featured=True,
        display_order=60,
        sources=source("Department of Tourism, Government of Maharashtra", "https://maharashtratourism.gov.in/heritage/deekshabhoomi/"),
    ),
    CuratedPlace(
        name="Takht Sachkhand Sri Hazur Sahib",
        district_slug="nanded",
        short_description="A major Sikh gurdwara and one of the five Takhts, located in Nanded.",
        description="Takht Sachkhand Sri Hazur Sahib is a major Sikh pilgrimage site in Nanded and one of Sikhism's five Takhts. The gurdwara commemorates Guru Gobind Singh, who died at Nanded in 1708, and remains an active centre of worship and Sikh heritage.",
        interest_slugs=("sacred-spiritual", "history-architecture"),
        spiritual_tradition=SpiritualTradition.SIKH,
        is_featured=True,
        display_order=70,
        sources=source("Nanded District, Government of Maharashtra", "https://nanded.gov.in/en/tourist-place/sachkhand-gurudwara/"),
    ),
    CuratedPlace(
        name="Haji Ali Dargah",
        district_slug="mumbai-city",
        short_description="A mosque and dargah on an islet off Worli in Mumbai.",
        description="Haji Ali Dargah is an active Islamic shrine and mosque situated on an islet off the Worli coast in Mumbai. A causeway connects the complex to the city shoreline, and its maritime setting has made it one of Mumbai's recognised religious landmarks.",
        interest_slugs=("sacred-spiritual", "history-architecture"),
        spiritual_tradition=SpiritualTradition.ISLAMIC,
        is_featured=True,
        display_order=80,
        sources=source("Mumbai City District, Government of Maharashtra", "https://mumbaicity.gov.in/en/tourist-place/haji-ali-dargah/"),
    ),
    CuratedPlace(
        name="Basilica of Our Lady of the Mount",
        district_slug="mumbai-suburban",
        short_description="A Roman Catholic basilica and pilgrimage shrine on Mount Mary hill in Bandra.",
        description="The Basilica of Our Lady of the Mount, commonly called Mount Mary Basilica, is an active Roman Catholic shrine in Bandra. The present stone church stands on a hill overlooking the Arabian Sea, while the site's Christian devotional history extends back to an earlier chapel.",
        interest_slugs=("sacred-spiritual", "history-architecture"),
        spiritual_tradition=SpiritualTradition.CHRISTIAN,
        is_featured=True,
        display_order=90,
        sources=source("Basilica of Our Lady of the Mount", "https://mountmarybasilicabandra.in/"),
    ),
    CuratedPlace(
        name="Nemgiri Jain Temple Complex",
        district_slug="parbhani",
        short_description="A Digambara Jain pilgrimage complex in the hills near Jintur.",
        description="Nemgiri Jain Temple Complex lies in the hills near Jintur in Parbhani district. The active Digambara Jain pilgrimage site includes temples and cave shrines associated with the area's historic Jain community and preserves images of several Tirthankaras.",
        interest_slugs=("sacred-spiritual", "history-architecture"),
        spiritual_tradition=SpiritualTradition.JAIN,
        is_featured=True,
        display_order=100,
        sources=source("Parbhani District, Government of Maharashtra", "https://parbhani.gov.in/tourist-place/%E0%A4%B6%E0%A5%8D%E0%A4%B0%E0%A5%80-%E0%A4%A6%E0%A4%BF%E0%A4%97%E0%A4%82%E0%A4%AC%E0%A4%B0-%E0%A4%9C%E0%A5%88%E0%A4%A8/"),
    ),
)
