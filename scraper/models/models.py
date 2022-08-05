from datetime import datetime, time
from enum import Enum
from typing import Dict, Generator, List, Set, Tuple

from models.yaml_basemodel import YAMLBaseModel
from pydantic import AnyHttpUrl


class SourceType(Enum):
    fireside = "Fireside"
    jb_com = "JB.com"
    youtube = "YouTube"
    archive_org = "Archive.org"


class EpisodeLink(YAMLBaseModel):
    title: str
    url: str
    description: str | None


class ScrapedEpisode(YAMLBaseModel):
    show_slug: str
    guid: str | None
    episode: int | float
    title: str
    pub_date: datetime | None
    enclosure_url: AnyHttpUrl | None
    enclosure_src: SourceType | None
    youtube_url: AnyHttpUrl | None
    duration: time | None
    hosts: Set[str] = set()
    guests: Set[str] = set()
    description: str | None
    summary: str | None
    sponsors: Set[str] = set()
    chapters_url: AnyHttpUrl | None
    episode_links: List[EpisodeLink] = []
    tags: Set[str] = set()

    class Config:
        validate_assignment = True


class ScrapedEpisodes(YAMLBaseModel):
    __root__: Dict[str, ScrapedEpisode]

    def __iter__(self) -> Generator[Tuple[str, ScrapedEpisode], None, None]:
        yield from self.__root__.items()

    def __getitem__(self, ep_number: str) -> ScrapedEpisode | None:
        return self.__root__.get(ep_number)

    def __setitem__(self, ep_number: str, ep: ScrapedEpisode) -> None:
        self.__root__[ep_number] = ep


class Show(YAMLBaseModel):
    show_slug: str
    episodes: ScrapedEpisodes


class Shows(YAMLBaseModel):
    __root__: Dict[str, Show]

    def __iter__(self) -> Generator[Tuple[str, Show], None, None]:
        yield from self.__root__.items()

    def __getitem__(self, show_slug: str) -> Show:
        """Return an exisitng Show or a new empty Show"""
        show = self.__root__.get(show_slug)
        if not show:
            # Create and add a new empty Show object
            show = Show(show_slug=show_slug, episodes={})
            self.__root__[show_slug] = show
        return show

    def __setitem__(self, show_slug: str, show: Show) -> None:
        self.__root__[show_slug] = show
