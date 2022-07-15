from datetime import datetime, time
import json
from textwrap import indent
from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, AnyHttpUrl, HttpUrl, Json, root_validator, validator


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

    # Episode GUID
    # Source: Fireside json api: `items[n].id`
    episode_guid: str

    # Episode number again, but specifically for Hugo.
    # Need this since we want to have zero padded filenames (e.g. `0042.md`), but no 
    # zero padding in the link to the episdoe (e.g. `https://coder.show/42`).
    # Hugo will use the filename for the slug by default, unless this param is set to
    # override it:
    #   https://gohugo.io/content-management/organization/#slug
    # Source: Generated using `episode` above
    slug: str = ""

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

    # Chapters JSON in a format defined by podcastingindex.org:
    #   https://github.com/Podcastindex-org/podcast-namespace/blob/main/chapters/jsonChapters.md
    # Source: RSS feed from fireside
    podcast_chapters: Optional[Dict]

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
        cls._generate_slug(values)
        cls._delete_dup_links(values)
        return values

    @classmethod
    def _generate_slug(cls, values):
        """Set the episode number as the slug.
        """
        epnum = values.get("episode")
        values["slug"] = str(epnum)
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
    
    @classmethod
    def _delete_dup_links(cls, values):
        # podcast_alt_file from JB might have same link. If same - set to None
        try:
            file = values["podcast_file"]
            alt = values.get("podcast_alt_file")  # Optional
            if not alt:
                return values

            file = cls._rm_http_or_https(file)
            alt = cls._rm_http_or_https(alt)

            if alt == file:
                values["podcast_alt_file"] = None
            
            return values
        except:
            print(json.dumps(values, indent=2))

    @validator('youtube_link')
    def check_youtube_link(cls, v):
        if v:
            assert v.host in VALID_YOUTUBE_HOSTNAMES, f"host of the url must be one of {VALID_YOUTUBE_HOSTNAMES}, instead got {v.host}"
        return v

    @validator('podcast_file', 'podcast_alt_file', 'podcast_ogg_file', 'video_file', 'video_hd_file', 'video_mobile_file', pre=True)
    def remove_tracking(cls, v: Optional[str]):
        if not v:
            return v

        # Need this to add back the proper scheme later.
        # Video files from scale engine don't load using https, might be the case with 
        # other links.         
        scheme = "https://" if v.startswith("https://") else "http://"

        # Remove the scheme
        v = cls._rm_http_or_https(v)

        if v.startswith("www.podtrac.com/pts/redirect"):
            v = v.removeprefix("www.podtrac.com/pts/redirect")
            # Remove the file ext part before with the first slash, e.g. ".mp3/" or ".ogg/"
            v = v[v.find("/")+1:]

        if v.startswith("chtbl.com/track/"):
            v = v.removeprefix("chtbl.com/track/")
            v = v[v.find("/")+1:]  # remove the tracking + first slash ID e.g. "392D9/"
        
        # Add back scheme
        v = f"{scheme}{v}"

        return v

    @classmethod
    def _rm_http_or_https(cls, v: str) -> str:
        v = v.removeprefix("http://")
        v = v.removeprefix("https://")
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
