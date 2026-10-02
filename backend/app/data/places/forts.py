"""Reviewed fort and defensive-heritage records."""

from datetime import date

from app.data.places.types import CuratedPlace, SourceProvenance


VERIFIED_ON = date(2026, 9, 25)
FORTS_SOURCE = (
    SourceProvenance(
        "Department of Tourism, Government of Maharashtra",
        "https://maharashtratourism.gov.in/tourist-intrests/forts/",
        VERIFIED_ON,
    ),
)


FORT_PLACES: tuple[CuratedPlace, ...] = (
    CuratedPlace(
        name="Raigad Fort",
        district_slug="raigad",
        short_description="The hill fort that served as Chhatrapati Shivaji Maharaj's capital from his coronation in 1674.",
        description="Raigad Fort rises above the Mahad area in the Sahyadri range. Chhatrapati Shivaji Maharaj developed it as the capital of his kingdom and was crowned there in 1674. Surviving gateways, public and residential remains, water structures and defensive works reveal the scale of the former hill capital.",
        interest_slugs=("forts-heritage", "history-architecture"),
        is_featured=True,
        display_order=10,
        sources=FORTS_SOURCE,
    ),
    CuratedPlace(
        name="Sinhagad Fort",
        district_slug="pune",
        short_description="A historic hill fort near Pune, formerly known as Kondhana and closely associated with the 1670 battle.",
        description="Sinhagad Fort stands on a high ridge southwest of Pune and was earlier known as Kondhana. Its strategic setting and surviving gates reflect a long defensive history, while the 1670 battle associated with Tanaji Malusare remains one of the best-known episodes connected with the fort.",
        interest_slugs=("forts-heritage", "history-architecture"),
        is_featured=True,
        display_order=20,
        sources=(SourceProvenance("Pune District, Government of Maharashtra", "https://pune.gov.in/en/tourist-place/sinhagad/", VERIFIED_ON),),
    ),
    CuratedPlace(
        name="Pratapgad Fort",
        district_slug="satara",
        short_description="A seventeenth-century hill fort in Satara district overlooking the route near Mahabaleshwar.",
        description="Pratapgad Fort occupies a commanding ridge in Satara district near Mahabaleshwar. Built during the rule of Chhatrapati Shivaji Maharaj, its upper and lower fortifications, gateways and bastions reflect the defensive use of the steep Sahyadri terrain.",
        interest_slugs=("forts-heritage", "history-architecture"),
        display_order=30,
        sources=FORTS_SOURCE,
    ),
    CuratedPlace(
        name="Shivneri Fort",
        district_slug="pune",
        short_description="A fortified hill site at Junnar known as the birthplace of Chhatrapati Shivaji Maharaj.",
        description="Shivneri Fort overlooks Junnar in Pune district and is recognised as the birthplace of Chhatrapati Shivaji Maharaj. Its approach passes through a sequence of gates, while the plateau retains fortifications, water structures and buildings connected with its military history.",
        interest_slugs=("forts-heritage", "history-architecture"),
        display_order=40,
        sources=(SourceProvenance("Department of Tourism, Government of Maharashtra", "https://maharashtratourism.gov.in/districts/pune/", VERIFIED_ON),),
    ),
    CuratedPlace(
        name="Torna Fort",
        district_slug="pune",
        short_description="A large hill fort in Pune district associated with the early expansion of Chhatrapati Shivaji Maharaj's territory.",
        description="Torna Fort, also called Prachandagad, extends across a rugged Sahyadri ridge southwest of Pune. The fort is associated with the early phase of Chhatrapati Shivaji Maharaj's state and retains extensive walls, gateways and bastions adapted to the mountain terrain.",
        interest_slugs=("forts-heritage", "history-architecture"),
        display_order=50,
        sources=FORTS_SOURCE,
    ),
    CuratedPlace(
        name="Lohagad Fort",
        district_slug="pune",
        short_description="A hill fort near Lonavala distinguished by its fortified approach and long defensive history.",
        description="Lohagad Fort stands near Lonavala on a ridge overlooking historic routes through the Western Ghats. Its fortified gates and the long spur known as Vinchu Kata are prominent elements of a site that passed through several ruling powers and was used during the Maratha period.",
        interest_slugs=("forts-heritage", "history-architecture"),
        display_order=60,
        sources=FORTS_SOURCE,
    ),
    CuratedPlace(
        name="Panhala Fort",
        district_slug="kolhapur",
        short_description="An extensive Deccan hill fort overlooking the approaches to Kolhapur.",
        description="Panhala Fort occupies a broad hilltop northwest of Kolhapur. Its surviving gateways, bastions, granaries and water arrangements reflect its role as a major fortified centre under successive Deccan powers, including the Marathas.",
        interest_slugs=("forts-heritage", "history-architecture"),
        display_order=70,
        sources=FORTS_SOURCE,
    ),
    CuratedPlace(
        name="Sindhudurg Fort",
        district_slug="sindhudurg",
        short_description="A seventeenth-century sea fort built on an island off the Malvan coast.",
        description="Sindhudurg Fort was built during the rule of Chhatrapati Shivaji Maharaj on a rocky island off Malvan. Its substantial sea walls, concealed entrance and internal structures formed part of a fortified maritime network along the Konkan coast.",
        interest_slugs=("forts-heritage", "history-architecture", "beaches-coast"),
        is_featured=True,
        display_order=80,
        sources=FORTS_SOURCE,
    ),
    CuratedPlace(
        name="Murud-Janjira Fort",
        district_slug="raigad",
        short_description="A fortified island stronghold off Murud, noted for its stone walls and maritime setting.",
        description="Murud-Janjira Fort stands on an island in the Arabian Sea off the Raigad coast. Developed as the principal stronghold of the Siddis of Janjira, it preserves high stone walls, bastions, gateways and freshwater reservoirs within its maritime defences.",
        interest_slugs=("forts-heritage", "history-architecture", "beaches-coast"),
        display_order=90,
        sources=(SourceProvenance("Raigad District, Government of Maharashtra", "https://raigad.gov.in/en/tourist-places/", VERIFIED_ON),),
    ),
    CuratedPlace(
        name="Devgiri-Daulatabad Fort",
        district_slug="chhatrapati-sambhajinagar",
        short_description="A medieval fortified citadel, formerly Devgiri, built around a steep conical hill.",
        description="Devgiri, later known as Daulatabad, became the capital of the Yadava kingdom and subsequently passed through several medieval states. The fortified complex uses a steep hill, rock-cut defences, gateways, moats and passages to create successive defensive layers; later monuments include the Chand Minar.",
        interest_slugs=("forts-heritage", "history-architecture"),
        is_featured=True,
        display_order=100,
        sources=(SourceProvenance("Department of Tourism, Government of Maharashtra", "https://maharashtratourism.gov.in/fort/devgiri-daulatabad/", VERIFIED_ON),),
    ),
)
