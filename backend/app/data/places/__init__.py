"""Versioned curated Place dataset, intentionally separate from migrations."""

from app.data.places.beaches_coast import BEACH_COAST_PLACES
from app.data.places.caves import CAVE_PLACES
from app.data.places.forts import FORT_PLACES
from app.data.places.nature_hills import NATURE_HILL_PLACES
from app.data.places.sacred_spiritual import SACRED_SPIRITUAL_PLACES
from app.data.places.types import CuratedPlace, SourceProvenance
from app.data.places.wildlife_forests import WILDLIFE_FOREST_PLACES


CURATED_PLACES_V1: tuple[CuratedPlace, ...] = (
    *CAVE_PLACES,
    *FORT_PLACES,
    *SACRED_SPIRITUAL_PLACES,
    *NATURE_HILL_PLACES,
    *WILDLIFE_FOREST_PLACES,
    *BEACH_COAST_PLACES,
)

__all__ = ["CURATED_PLACES_V1", "CuratedPlace", "SourceProvenance"]
