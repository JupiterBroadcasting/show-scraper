from datetime import datetime, time
from typing import List, Literal, Optional
from pydantic import BaseModel, AnyHttpUrl, HttpUrl, root_validator, validator


VALID_YOUTUBE_HOSTNAMES = {"youtube.com", "www.youtube.com", "youtu.be",  "www.youtu.be"}


class Episode(BaseModel):

    # Hardcoded
    type: Literal["episode"] = "episode"

    # Default to False for all past shows
    draft: bool = False

    # Source: defined in `config.yml` (the key of each show)
    show_slug: str

    # Source: defined in `config.yml` as `name`
    show_name: str

    # Episode number
    # Source: fireside website of each show
    episode: int

    # Episode number padded with 3 zeros. Generated from `episode`
    episode_padded: str

    # Source: fireside website of each show
    title: str

    # Source: fireside website of each show
    description: str

    # ISO 8601 Date "YYYY-MM-DD"
    # Source: fireside website of each show
    date: datetime

    # Generated value from `show_slug`
    header_image: str = "/images/shows/default.png"

    # Source: hardcoded show name from fireside-scraper/config.yml
    categories: List[str] = []

    # Source: fireside website of each show
    tags: List[str]

    # Source: fireside website of each show
    hosts: List[str]

    # Source: fireside website of each show
    guests: List[str]

    # Constructed using link domain and show acronym from configl.yml
    # Example:
    #   ["linode.com-lup", "linode.com-cr", "bitwarden.com-lup"]
    # Source: fireside website of each show
    sponsors: List[str]

    # Duration in hh:mm:ss format
    # Source: fireside website of each show
    podcast_duration: time

    # Example:
    #   "https://chtbl.com/track/392D9/aphid.fireside.fm/d/1437767933/f31a453c-fa15-491f-8618-3f71f1d565e5/79855861-037c-4e37-81c9-36a795764341.mp3"
    # Source: fireside website of each show
    podcast_file: AnyHttpUrl

    # Number of bytes of the `podcast_file` above (from fireside)
    # Source: fireside
    podcast_bytes: int

    # Has different tracking url than `podcast_file`
    # Example:
    #   "http://www.podtrac.com/pts/redirect.mp3/traffic.libsyn.com/jnite/lup-0116.mp3"
    # Source: jupiterbroadcasting.com "Direct Download" links -> "MP3 Audio"
    podcast_alt_file: Optional[AnyHttpUrl]

    # Source: jupiterbroadcasting.com "Direct Download" links -> "OGG Audio""
    podcast_ogg_file: Optional[AnyHttpUrl]

    # Source: jupiterbroadcasting.com "Direct Download" -> "Video"
    video_file: Optional[AnyHttpUrl]

    # Source: jupiterbroadcasting.com "Direct Download" -> "HD Video"
    video_hd_file: Optional[AnyHttpUrl]

    # Source: jupiterbroadcasting.com "Direct Download" -> "Mobile Video"
    video_mobile_file: Optional[AnyHttpUrl]

    # Source: jupiterbroadcasting.com "Direct Download" -> "YouTube"
    youtube_link: Optional[HttpUrl]

    # Path part of the URL to the episode page on jupiterbroadcasting.com
    # Example:
    #     "/149032/git-happens-linux-unplugged-464/"
    # Source: jupiterbroadcasting.com
    jb_url: Optional[str]

    # Path part of the URL to the episode page on show's fireside website
    # Example:
    #   "/42"
    fireside_url: str

    # Markdown list with links and some descriptions
    # Source: fireside website of each show
    episode_links: Optional[str]

    @root_validator(pre=False)
    def _generate_fields(cls, values: dict) -> dict:
        """Automatically generate some value for fields based on other fields or
        predefined rules.
        """
        cls._generate_header_image(values)
        cls._generate_categories(values)
        return values

    @classmethod
    def _generate_categories(cls, values):
        """Make sure the show name is in categories and is the first one.
        """
        show_name = values.get("show_name")

        cats: List = values.get("categories", [])
        if show_name not in cats:
            cats.insert(0, show_name)
        values["categories"] = cats

    @classmethod
    def _generate_header_image(cls, values):
        slug = values.get("show_slug")
        values["header_image"] = f"/images/shows/{slug}.png"

    @validator('youtube_link')
    def check_youtube_link(cls, v):
        if v:
            assert v.host in VALID_YOUTUBE_HOSTNAMES, f"host of the url must be one of {VALID_YOUTUBE_HOSTNAMES}, instead got {v.host}"
        return v


    def get_hugo_md_file_content(self) -> str:
        """Constructs and returns the content of the Hugo markdown file.
        """
        
        content = self.json(exclude={"episode_links"}, indent=2)
        content += "\n"

        if self.episode_links:
            content += "\n\n"
            content += "### Episode Links\n\n"
            content += self.episode_links
        
        content += "\n"  # Empty line

        return content
