"""Authoritative-source-reviewed Culture & Traditions stories."""

from datetime import date

from app.data.discovery_stories.types import CuratedDiscoveryStory, PlaceReference
from app.data.provenance import SourceProvenance


VERIFIED_ON = date(2026, 9, 28)


def sources(*items: tuple[str, str]) -> tuple[SourceProvenance, ...]:
    return tuple(SourceProvenance(name, url, VERIFIED_ON) for name, url in items)


CULTURE_STORIES: tuple[CuratedDiscoveryStory, ...] = (
    CuratedDiscoveryStory(
        title="Pandharpur Wari",
        short_description="A living pilgrimage tradition in which Warkari communities journey towards Pandharpur in devotion to Vitthal.",
        body="The Pandharpur Wari is a devotional journey associated with Maharashtra's Warkari tradition and the Vitthal-Rukmini temple at Pandharpur. Groups of pilgrims travel together through shared practices of walking, singing and remembrance. Maharashtra Tourist Places presents the Wari as a living cultural and spiritual tradition rather than a fixed event product; travellers should confirm current procession arrangements and local guidance before planning a visit.",
        interest_slugs=("culture-traditions", "sacred-spiritual"),
        district_slugs=("solapur",),
        related_place_references=(PlaceReference("solapur", "shri-vitthal-rukmini-temple"),),
        is_featured=True,
        display_order=10,
        sources=sources(
            ("Department of Tourism, Government of Maharashtra", "https://maharashtratourism.gov.in/temple/pandharpur/"),
            ("Solapur District, Government of Maharashtra", "https://solapur.gov.in/en/tourist-place/pandharpur/"),
        ),
    ),
    CuratedDiscoveryStory(
        title="Lavani Performance Tradition",
        short_description="A Marathi performance tradition bringing together composed verse, expressive movement, rhythm and stagecraft.",
        body="Lavani is a performance tradition of Maharashtra in which poetry and song are closely joined with rhythm and expressive movement. Government cultural references document Lavani alongside Maharashtra's wider folk-performance landscape and its connections with forms such as Tamasha. The tradition contains varied repertoires and performance settings, so this introduction avoids treating any one presentation as the complete form.",
        interest_slugs=("culture-traditions",),
        is_featured=True,
        display_order=20,
        sources=sources(
            ("Maharashtra State Gazetteers", "https://gazetteers.maharashtra.gov.in/cultural.maharashtra.gov.in/english/gazetteer/land_and_people/L%20%26%20P%20pdf/Chapter%20VIII/2%20Music.pdf"),
            ("Centre for Cultural Resources and Training, Government of India", "https://ccrtindia.gov.in/789-2/"),
        ),
    ),
    CuratedDiscoveryStory(
        title="Warli Art and Community Storytelling",
        short_description="An Indigenous visual tradition associated with Warli communities in and around Maharashtra's Palghar region.",
        body="Warli painting is an Indigenous visual tradition rooted in community life in the Palghar region. Maharashtra Tourism describes the art in relation to everyday activity, nature, ritual and storytelling, while Palghar's official tourism material places it within the district's broader tribal cultural landscape. This story recognises the tradition as living community knowledge and does not reduce it to a decorative motif.",
        interest_slugs=("culture-traditions",),
        district_slugs=("palghar",),
        is_featured=True,
        display_order=30,
        sources=sources(
            ("Department of Tourism, Government of Maharashtra", "https://maharashtratourism.gov.in/districts/palghar/"),
            ("Department of Tourism, Government of Maharashtra", "https://maharashtratourism.gov.in/nature/jawhar/"),
        ),
    ),
    CuratedDiscoveryStory(
        title="Paithani Weaving",
        short_description="A handwoven silk tradition associated with Paithan and the important weaving centre of Yeola.",
        body="Paithani is a handwoven silk tradition named for Paithan and sustained through skilled weaving communities in more than one part of Maharashtra. Official handloom documentation identifies Paithan and Yeola as significant geographies, while the Indian GI registry records Paithani Sarees and Fabrics as a registered geographical indication. The story therefore links both Chhatrapati Sambhajinagar and Nashik districts without claiming exclusive ownership for either.",
        interest_slugs=("culture-traditions",),
        district_slugs=("chhatrapati-sambhajinagar", "nashik"),
        is_featured=True,
        display_order=40,
        sources=sources(
            ("Development Commissioner for Handlooms, Government of India", "https://handlooms.nic.in/assets/img/Publications/Paithani%20sarees%20and%20Dress%20Materials635701517283000941.pdf"),
            ("Nashik District, Government of Maharashtra", "https://nashik.gov.in/en/district-industries-centre/"),
            ("Geographical Indications Registry, Government of India", "https://search.ipindia.gov.in/GIRPublicSearch/Application/Details/150"),
        ),
    ),
    CuratedDiscoveryStory(
        title="Ganeshotsav Traditions Across Maharashtra",
        short_description="Home and community observances that bring devotion, craft, music and neighbourhood participation together.",
        body="Ganeshotsav in Maharashtra is expressed through both household observance and public community celebration. Maharashtra Tourism documents worship, aarti, cultural programmes, shared food traditions and immersion as parts of the festival's public life. Practices vary between families and communities, and annual dates and local arrangements change, so this story focuses on enduring cultural context rather than a current event schedule.",
        interest_slugs=("culture-traditions", "sacred-spiritual"),
        is_featured=True,
        display_order=50,
        sources=sources(
            ("Department of Tourism, Government of Maharashtra", "https://maharashtratourism.gov.in/mr/festivals/%E0%A4%97%E0%A4%A3%E0%A5%87%E0%A4%B6-%E0%A4%9A%E0%A4%A4%E0%A5%81%E0%A4%B0%E0%A5%8D%E0%A4%A5%E0%A5%80/"),
        ),
    ),
)
