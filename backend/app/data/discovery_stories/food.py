"""Authoritative-source-reviewed Food & Local Flavours stories."""

from datetime import date

from app.data.discovery_stories.types import CuratedDiscoveryStory
from app.data.provenance import SourceProvenance


VERIFIED_ON = date(2026, 9, 28)
FLAVOURS_SOURCE = SourceProvenance(
    "Department of Tourism, Government of Maharashtra",
    "https://maharashtratourism.gov.in/flavors-of-maharashtra/",
    VERIFIED_ON,
)


FOOD_STORIES: tuple[CuratedDiscoveryStory, ...] = (
    CuratedDiscoveryStory(
        title="Varhadi Cuisine of Vidarbha",
        short_description="A regional food tradition of Vidarbha shaped by bold seasoning and locally familiar grains, pulses and spices.",
        body="Varhadi cuisine belongs to the wider Vidarbha region rather than to one exclusive district. Maharashtra Tourism characterises the tradition through robust seasoning and ingredients such as chickpea flour, mustard, sesame and spices. This introduction treats those features as broad regional context, not as a single canonical menu or recipe.",
        interest_slugs=("food-local-flavours",),
        is_featured=True,
        display_order=10,
        sources=(FLAVOURS_SOURCE,),
    ),
    CuratedDiscoveryStory(
        title="Saoji Cuisine of Nagpur",
        short_description="A Nagpur-associated culinary tradition known for deeply seasoned gravies and distinctive spice blends.",
        body="Saoji cuisine is closely associated with Nagpur and is commonly described through richly seasoned gravies and characteristic spice blends. Maharashtra Tourism includes it within the regional cuisines of the state. Preparations vary by cook and community, so Maharashtra Tourist Places does not present one formula as definitive or make claims about a single originator.",
        interest_slugs=("food-local-flavours",),
        district_slugs=("nagpur",),
        is_featured=True,
        display_order=20,
        sources=(FLAVOURS_SOURCE,),
    ),
    CuratedDiscoveryStory(
        title="Kolhapuri Cuisine",
        short_description="Kolhapur's regional cooking tradition, recognised for assertive spice, bhakri and contrasting gravies.",
        body="Kolhapuri cuisine is strongly associated with Kolhapur district and is known for assertive spice and distinctive local preparations. Official tourism material highlights dishes such as tambda rassa and pandhara rassa alongside bhakri. The tradition includes vegetarian and non-vegetarian foodways, and this overview avoids reducing it to heat alone.",
        interest_slugs=("food-local-flavours",),
        district_slugs=("kolhapur",),
        is_featured=True,
        display_order=30,
        sources=(
            FLAVOURS_SOURCE,
            SourceProvenance("Department of Tourism, Government of Maharashtra", "https://maharashtratourism.gov.in/districts/kolhapur/", VERIFIED_ON),
        ),
    ),
    CuratedDiscoveryStory(
        title="Malvani Cuisine of the Konkan Coast",
        short_description="A coastal food tradition associated with Malvan and the wider Konkan, where coconut, kokum and seafood are recurring elements.",
        body="Malvani cuisine is associated with Malvan and the Konkan coast. Maharashtra Tourism describes the tradition through aromatic spice blends, coconut and coconut milk, with seafood prominent in many coastal preparations. The cuisine is not limited to a single dish, and local household and community practices remain diverse.",
        interest_slugs=("food-local-flavours",),
        district_slugs=("sindhudurg",),
        is_featured=True,
        display_order=40,
        sources=(FLAVOURS_SOURCE,),
    ),
    CuratedDiscoveryStory(
        title="Puran Poli and Modak at Festival Tables",
        short_description="Two sweets that appear in Maharashtra's festival food traditions across homes and communities.",
        body="Puran poli and modak appear in Maharashtra's festival food traditions, including observances connected with Ganesh Chaturthi and Mangalagaur. Official tourism material describes several forms and contexts rather than one mandatory recipe. This statewide story focuses on their place at shared and household tables without claiming that either preparation belongs exclusively to one district.",
        interest_slugs=("food-local-flavours",),
        is_featured=True,
        display_order=50,
        sources=(
            SourceProvenance("Department of Tourism, Government of Maharashtra", "https://maharashtratourism.gov.in/mr/festivals/%E0%A4%97%E0%A4%A3%E0%A5%87%E0%A4%B6-%E0%A4%9A%E0%A4%A4%E0%A5%81%E0%A4%B0%E0%A5%8D%E0%A4%A5%E0%A5%80/", VERIFIED_ON),
            SourceProvenance("Department of Tourism, Government of Maharashtra", "https://maharashtratourism.gov.in/culture/mangalagaur/", VERIFIED_ON),
        ),
    ),
)
