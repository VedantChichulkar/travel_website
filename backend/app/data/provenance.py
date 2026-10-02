from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class SourceProvenance:
    """Internal review metadata for operator-managed curated content."""

    source_name: str
    source_url: str
    source_last_verified_at: date
