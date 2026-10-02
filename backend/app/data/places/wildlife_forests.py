"""Reviewed wildlife and protected-forest Place records."""

from datetime import date

from app.data.places.types import CuratedPlace, SourceProvenance


VERIFIED_ON = date(2026, 9, 27)


def source(name: str, url: str) -> tuple[SourceProvenance, ...]:
    return (SourceProvenance(name, url, VERIFIED_ON),)


WILDLIFE_FOREST_PLACES: tuple[CuratedPlace, ...] = (
    CuratedPlace(
        name="Tadoba-Andhari Tiger Reserve",
        district_slug="chandrapur",
        short_description="A tiger reserve in Chandrapur comprising Tadoba National Park and Andhari Wildlife Sanctuary.",
        description="Tadoba-Andhari Tiger Reserve is a protected forest landscape in Chandrapur district. Its core includes Tadoba National Park and Andhari Wildlife Sanctuary, with dry deciduous forest, grasslands and water bodies supporting a varied wildlife community.",
        interest_slugs=("wildlife-forests",),
        is_featured=True,
        display_order=10,
        sources=source("Tadoba-Andhari Tiger Reserve, Maharashtra Forest Department", "https://mytadoba.mahaforest.gov.in/"),
    ),
    CuratedPlace(
        name="Pench Tiger Reserve, Maharashtra",
        district_slug="nagpur",
        short_description="A protected forest landscape in Nagpur district centred on Pench National Park and the Pench River.",
        description="Maharashtra's Pench Tiger Reserve lies in Nagpur district along the Pench River and includes Pench National Park. Its teak-dominated forests form part of a larger ecological landscape that continues across the state boundary into Madhya Pradesh.",
        interest_slugs=("wildlife-forests",),
        is_featured=True,
        display_order=20,
        sources=source("Maharashtra Forest Department", "https://mahaforest.gov.in/index.php/projecttiger/index/en"),
    ),
    CuratedPlace(
        name="Melghat Tiger Reserve",
        district_slug="amravati",
        short_description="A Satpura tiger reserve in Amravati district containing Gugamal National Park and Melghat Wildlife Sanctuary.",
        description="Melghat Tiger Reserve extends across the forested Satpura and Gawilgarh hills of Amravati district. The protected landscape includes Gugamal National Park and Melghat Wildlife Sanctuary and was among India's original Project Tiger reserves.",
        interest_slugs=("wildlife-forests",),
        is_featured=True,
        display_order=30,
        sources=source("Maharashtra Forest Department", "https://mahaforest.gov.in/index.php/projecttiger/index/en"),
    ),
    CuratedPlace(
        name="Navegaon National Park",
        district_slug="gondia",
        short_description="A national park in southern Gondia district protecting forest, wetland and wildlife habitat.",
        description="Navegaon National Park lies in the southern part of Gondia district. Forest, lake and wetland habitats support diverse bird, reptile and mammal communities and form part of an important conservation landscape in eastern Maharashtra.",
        interest_slugs=("wildlife-forests",),
        display_order=40,
        sources=source("Gondia District, Government of Maharashtra", "https://gondia.gov.in/en/places-of-interest/"),
    ),
    CuratedPlace(
        name="Tipeshwar Wildlife Sanctuary",
        district_slug="yavatmal",
        short_description="A wildlife sanctuary of hilly dry forest in Pandharkawada tehsil, Yavatmal district.",
        description="Tipeshwar Wildlife Sanctuary is situated in Pandharkawada tehsil of Yavatmal district. Its undulating terrain supports varied vegetation and habitat for mammals and birds within a protected dry-forest landscape.",
        interest_slugs=("wildlife-forests",),
        display_order=50,
        sources=source("Yavatmal District, Government of Maharashtra", "https://yavatmal.gov.in/en/tourist-place/name-of-tourist-place-to-visit/"),
    ),
    CuratedPlace(
        name="Radhanagari Wildlife Sanctuary",
        district_slug="kolhapur",
        short_description="A Western Ghats wildlife sanctuary in Kolhapur district known for its forest and gaur habitat.",
        description="Radhanagari Wildlife Sanctuary protects a forested Western Ghats landscape in Kolhapur district. Managed by the Kolhapur Wildlife Division, its evergreen and semi-evergreen habitats are particularly associated with gaur and other native wildlife.",
        interest_slugs=("wildlife-forests",),
        display_order=60,
        sources=source("Maharashtra Forest Department", "https://mahaforest.gov.in/writereaddata/managementpdf/1437476002kolhapur%20Vol.%20I.pdf"),
    ),
)
