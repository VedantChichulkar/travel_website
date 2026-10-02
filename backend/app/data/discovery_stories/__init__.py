from app.data.discovery_stories.culture import CULTURE_STORIES
from app.data.discovery_stories.food import FOOD_STORIES
from app.data.discovery_stories.types import CuratedDiscoveryStory


CURATED_DISCOVERY_STORIES: tuple[CuratedDiscoveryStory, ...] = CULTURE_STORIES + FOOD_STORIES

__all__ = ["CURATED_DISCOVERY_STORIES", "CULTURE_STORIES", "FOOD_STORIES"]
