"""Reviewed beach and coastal Place records."""

from datetime import date

from app.data.places.types import CuratedPlace, SourceProvenance
from app.models.place import SpiritualTradition


VERIFIED_ON = date(2026, 9, 27)


def source(name: str, url: str) -> tuple[SourceProvenance, ...]:
    return (SourceProvenance(name, url, VERIFIED_ON),)


MAHARASHTRA_TOURISM = "Department of Tourism, Government of Maharashtra"


BEACH_COAST_PLACES: tuple[CuratedPlace, ...] = (
    CuratedPlace(
        name="Ganpatipule Beach and Temple",
        district_slug="ratnagiri",
        short_description="A Konkan beach settlement centred on an active Ganapati temple beside the Arabian Sea.",
        description="Ganpatipule combines a broad Arabian Sea beach with an active Ganapati temple in Ratnagiri district. The temple is the settlement's principal pilgrimage landmark, while the adjoining shore forms one of the district's established coastal visitor places.",
        interest_slugs=("beaches-coast", "sacred-spiritual"),
        spiritual_tradition=SpiritualTradition.HINDU,
        is_featured=True,
        display_order=10,
        sources=source("Ratnagiri District, Government of Maharashtra", "https://ratnagiri.gov.in/en/tourist-place/ganapati-pule-temple/"),
    ),
    CuratedPlace(
        name="Tarkarli Beach",
        district_slug="sindhudurg",
        short_description="A sandy Konkan beach near Malvan on the Sindhudurg coast.",
        description="Tarkarli Beach lies on the Konkan coast near Malvan in Sindhudurg district. Its long sandy shoreline and coastal waters connect the beach with the wider maritime landscape around the Karli estuary and Sindhudurg's sea-fort heritage.",
        interest_slugs=("beaches-coast",),
        is_featured=True,
        display_order=20,
        sources=source(MAHARASHTRA_TOURISM, "https://maharashtratourism.gov.in/beach/tarkarli/"),
    ),
    CuratedPlace(
        name="Alibag Beach",
        district_slug="raigad",
        short_description="The principal town beach at Alibag, facing Kolaba Fort across the tidal shore.",
        description="Alibag Beach is the main urban beach of Alibag in Raigad district. Its flat tidal shore faces Kolaba Fort offshore and forms a prominent public waterfront on the northern Konkan coast.",
        interest_slugs=("beaches-coast",),
        is_featured=True,
        display_order=30,
        sources=source("Raigad District, Government of Maharashtra", "https://raigad.gov.in/en/tourist-place/famous-beaches-in-raigad/"),
    ),
    CuratedPlace(
        name="Harihareshwar Beach",
        district_slug="raigad",
        short_description="A sandy shore at Harihareshwar on the southern Raigad coast.",
        description="Harihareshwar Beach lies beside the coastal town and Kalbhairav temple precinct in Raigad district. The shore opens onto the Arabian Sea near the southern end of the Shrivardhan Bay landscape.",
        interest_slugs=("beaches-coast",),
        display_order=40,
        sources=source("Raigad District, Government of Maharashtra", "https://raigad.gov.in/en/tourist-place/famous-beaches-in-raigad/"),
    ),
    CuratedPlace(
        name="Diveagar Beach",
        district_slug="raigad",
        short_description="A sandy Konkan beach in Shrivardhan taluka bordered by coastal village vegetation.",
        description="Diveagar Beach lies in Shrivardhan taluka of Raigad district. The village shore combines a long sandy beach with the coconut and betel-nut landscape characteristic of this part of the Konkan coast.",
        interest_slugs=("beaches-coast",),
        display_order=50,
        sources=source(MAHARASHTRA_TOURISM, "https://maharashtratourism.gov.in/beach/diveagar/"),
    ),
    CuratedPlace(
        name="Kashid Beach",
        district_slug="raigad",
        short_description="A sandy Arabian Sea beach on the Alibag-Murud coastal route.",
        description="Kashid Beach lies on the Alibag-Murud route in Raigad district. Its pale sand, open shoreline and coastal vegetation form a distinct beach landscape between the district's northern and southern maritime centres.",
        interest_slugs=("beaches-coast",),
        display_order=60,
        sources=source("Raigad District, Government of Maharashtra", "https://raigad.gov.in/en/tourist-place/famous-beaches-in-raigad/"),
    ),
    CuratedPlace(
        name="Guhagar Beach",
        district_slug="ratnagiri",
        short_description="A long sandy beach bordered by coconut and betel-nut plantations in northern Ratnagiri district.",
        description="Guhagar Beach extends along the Arabian Sea in northern Ratnagiri district. The sandy shore is backed by a coastal settlement and plantations, linking the beachfront with the wider creek, temple and village landscapes of the Guhagar area.",
        interest_slugs=("beaches-coast",),
        display_order=70,
        sources=source(MAHARASHTRA_TOURISM, "https://maharashtratourism.gov.in/beach/guhagar/"),
    ),
)
