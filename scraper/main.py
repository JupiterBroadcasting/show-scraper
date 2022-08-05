#!/usr/bin/env python3

import asyncio as aio
from email.utils import parsedate_to_datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import typer
import yaml
from bs4 import BeautifulSoup, NavigableString, ResultSet, Tag
from loguru import logger
from models import EpisodeLink, ScrapedEpisode, Shows
from pydantic import HttpUrl
from utils import capitalize_text, http


class ScrapeMode(str, Enum):
    full = "full"
    latest = "latest"


class Scraper:
    """Scraper class that handles scraper JB shows.

    The goal of this scraper is to collect a big picture of the JB
    episodes (archived and current shows). Mainly we care about media files, but other
    episode data:
    - Episode notes/links
    - Hosts & guests
    - Sponsors

    We only need a media item for each episode of each show, not necessarily to know
    every possible source.

    Logic:
    - if on fireside, then use that and halt.
    - if not on fireside, then look at jb.com. If found, use that and halt.
    - if not on the above, look at... YT?
    - if not there, then finally search archive.org
    """

    shows: Shows
    scrape_mode: ScrapeMode
    config: Dict[str, Any]  # TODO: load the "shows" from config into "self.shows"
    loop: aio.AbstractEventLoop

    def __init__(self, config_file_path: Path, scrape_mode: ScrapeMode) -> None:
        self.shows = Shows(__root__={})
        self.scrape_mode = scrape_mode
        self.config = self._read_config_file(config_file_path)
        self.loop = aio.get_event_loop()

    def _read_config_file(self, config_file_path: Path) -> Dict[str, Any]:
        try:
            with open(config_file_path) as f:
                return yaml.load(f, Loader=yaml.SafeLoader)
        except FileNotFoundError as e:
            logger.error(
                f"Failed to read config file: {config_file_path}\n Reason: {e}"
            )
            exit(1)  # Abort execution!

    def run(self) -> None:
        logger.info(f"Scraper started using the `{self.scrape_mode}` mode.")

        self.loop.run_until_complete(self.scrape_rss_feeds())

        # self.scrape_jb_website()

        with open("out.json", "w") as f:
            f.write(self.shows.json(exclude_none=True, indent=2))

        logger.info("Done :)")

    def _jb_scrape_ep_pages(self, jb_show_url: HttpUrl) -> Dict[str, str]:
        # TODO
        return {}

    @staticmethod
    def _find_next_sibling_tag(
        soup: BeautifulSoup,
        pre_title: str,
        find_tag: str = "p",
        sibling_tag: str = "ul",
    ) -> Tag | NavigableString | None:
        pre_element = soup.find(find_tag, string=pre_title)
        if pre_element is None:
            return None
        return pre_element.find_next_sibling(sibling_tag)

    @staticmethod
    def _get_plain_title(title: str) -> str:
        """Get just the show title, without any numbering etc"""
        # Remove number before colon
        title = title.split(":", 1)[-1]

        # Remove data after the pipe
        title = title.rsplit("|", 1)[0]

        # Strip any stray spaces
        return title.strip()

    def scrape_jb_website(self) -> None:
        for show_slug, show_conf in self.config["shows"].items():
            show = self.shows[show_slug]  # noqa

            jb_url = show_conf.get("jb_url")
            if not jb_url:
                continue

            # 1 Collect episode URLs
            ep_page_map = self._jb_scrape_ep_pages(jb_url)

            for ep, html_page in ep_page_map.items():
                page_bs = BeautifulSoup(html_page, "lxml")
                _title_tag = page_bs.find("title")

                assert _title_tag is not None, "Failed to find <title> in the HTML page"

                _title_tag.text.split("|")[0].strip()

                # show.get(ep)

                dl_links = self._jb_get_direct_download_links(show_slug, ep, page_bs)

                if dl_links:
                    for link in dl_links:
                        url = link.get("href").strip('\\"')
                        link.text.lower().replace(" ", "_")

    def _jb_get_direct_download_links(
        self, show_slug: str, ep: str, page_bs: BeautifulSoup
    ) -> Optional[ResultSet]:
        dd_div = page_bs.find("div", attrs={"id": "direct-downloads"})
        if isinstance(dd_div, Tag):
            return dd_div.find_all("a")
        else:
            # Older episodes have different structure.
            p_links = self._find_next_sibling_tag(
                page_bs, "Direct Download:", find_tag="h3", sibling_tag="p"
            )
            if isinstance(p_links, Tag):
                return p_links.find_all("a")
            else:
                logger.warning(
                    "Failed to find Direct Download links! "
                    f"show: {show_slug} ep: {ep}"
                )
        return None

    async def scrape_rss_feeds(self) -> None:
        tasks: Dict[str, aio.Task[str]] = {}

        for show_slug, show_conf in self.config["shows"].items():
            show = self.shows[show_slug]  # noqa
            rss_url: str = show_conf.get("rss_url")
            if not rss_url:
                continue
            tasks[show_slug] = aio.create_task(http.get_text(rss_url))

        for show_slug, task in tasks.items():
            try:
                show_xml = await task
                self._parse_show_rss_feed(show_slug, show_xml)
            except Exception as e:
                logger.error(
                    f"Failed to retreive the RSS feed of `{show_slug}`! Exception: {e}"
                )
                continue
        await self._clear_all_broken_urls()

    async def _clear_all_broken_urls(self) -> None:
        """Need to run this after each source has been scraped.
        This would ensure that the next source (JB.com, archive.org, or any other)
        will attempt to populate the unset URLs
        """

        tasks: List[Tuple[ScrapedEpisode, str, aio.Task[bool]]] = []
        for _, show in self.shows:
            for _, ep in show.episodes:
                if ep.enclosure_url:
                    tasks.append(
                        (
                            ep,
                            "enclosure_url",
                            aio.create_task(http.test_url(ep.enclosure_url)),
                        )
                    )
                if ep.chapters_url:
                    tasks.append(
                        (
                            ep,
                            "chapters_url",
                            aio.create_task(http.test_url(ep.chapters_url)),
                        )
                    )

        for ep, url_field, url_ok in tasks:
            try:
                if not await url_ok:
                    raise ValueError("Broken URL")
            except Exception as e:
                logger.warning(
                    f"{ep.show_slug} #{ep.episode} | "
                    f"Found a broken URL for `{url_field}`: {getattr(ep, url_field)}\n"
                    f"Exception: {e}"
                )
                # Clear the URL inside the Episode object
                setattr(ep, url_field, None)

    def _parse_show_rss_feed(self, show_slug: str, show_xml: str) -> None:
        logger.debug(f"Parsing show: `{show_slug}`")
        feed_bs = BeautifulSoup(show_xml, "lxml-xml")
        for item_bs in feed_bs.find_all("item"):
            self._parse_ep_item_from_rss(show_slug, item_bs)

    def _parse_ep_item_from_rss(self, show_slug: str, item_bs: Tag) -> None:
        ep_num = None
        try:
            show = self.shows[show_slug]
            assert show is not None, f"Show `{show_slug}` not found in `self.shows`!"

            show_config = self.config["shows"].get(show_slug)
            assert show_config is not None, f"Show config not found for `{show_slug}`!"

            # Get the episode number

            # Try <podcast:episode>
            _pod_episode = item_bs.find("podcast:episode")
            if _pod_episode:
                ep_num = _pod_episode.text

            # Fallback to getting it from <link> URL value
            if not ep_num:
                _link = item_bs.find("link")
                if _link:
                    _ep = _link.text.split("/")[-1]
                    try:
                        # Validate that it is number, but still keep the value as string
                        float(_ep)
                        ep_num = _ep
                    except:  # noqa
                        pass

            if not ep_num:
                raise ValueError(
                    "Failed to extract the episode number! "
                    "Cannot continue as it is a must have."
                )

            logger.debug(f"Parsing episode: `{show_slug}` #{ep_num}")

            _title = item_bs.find("title")
            if not _title:
                raise ValueError("Failed to find a <title> inside an <item>!")

            title = self._get_plain_title(_title.text)

            episode = show.episodes[ep_num]
            if not episode:
                # Create new episode object
                episode = ScrapedEpisode(
                    show_slug=show_slug, episode=ep_num, title=title
                )
                show.episodes[ep_num] = episode

            if not episode.guid:
                _guid = item_bs.find("guid")
                if _guid:
                    episode.guid = _guid.text

            if not episode.pub_date:
                _pub_date = item_bs.find("pubDate")
                if _pub_date:
                    episode.pub_date = parsedate_to_datetime(_pub_date.text)

            if not episode.enclosure_url:
                _enclosure = item_bs.find("enclosure")
                if _enclosure:
                    episode.enclosure_url = _enclosure.get("url")  # type: ignore
                    episode.enclosure_src = show_config.get("rss_src")

            if not episode.chapters_url:
                _chapters = item_bs.find("podcast:chapters")
                if _chapters:
                    episode.chapters_url = _chapters.get("url")  # type: ignore

            if not episode.description:
                _description = item_bs.find("description")
                if _description:
                    episode.description = _description.text

            _keywords = item_bs.find("itunes:keywords")
            if _keywords:
                for tag in _keywords.text.split(","):
                    episode.tags.add(tag.lower().strip())

            _persons = item_bs.find_all("podcast:person")
            for p in _persons:
                _role = p.get("role", "host")
                if _role == "host":
                    episode.hosts.add(capitalize_text(p.text))
                elif _role == "guest":
                    episode.guests.add(capitalize_text(p.text))

            _summary = item_bs.find("content:encoded")
            if not _summary:
                _summary = item_bs.find("itunes:summary")
            if _summary:
                episode.summary = _summary.text

                summary_bs = BeautifulSoup(_summary.text, "lxml")
                _links_ul_bs = self._find_next_sibling_tag(summary_bs, "Links:")
                if not _links_ul_bs:
                    _links_ul_bs = self._find_next_sibling_tag(
                        summary_bs, "Episode Links:"
                    )
                if isinstance(_links_ul_bs, Tag):
                    for li in _links_ul_bs.find_all("li"):
                        _a = li.find("a")
                        url = _a.get("href")
                        title = _a.text

                        desc = li.contents[1].string if len(li.contents) == 2 else None
                        if desc:
                            desc = desc.removeprefix(" — ")  # &mdash;
                            desc = desc.replace("\r\n", "")
                            desc = desc.strip()

                        ep_link = EpisodeLink(title=title, url=url, description=desc)
                        episode.episode_links.append(ep_link)
        except Exception as e:
            logger.error(
                f"Failed to parse `{show_slug}` episode #{ep_num} from RSS feed! "
                f"Exception: {e}"
            )


app = typer.Typer(pretty_exceptions_show_locals=False)


@app.command()
def main(
    config: Path = typer.Option(Path("./config.yml")),
    scrape_mode: ScrapeMode = typer.Option(ScrapeMode.latest.value),
) -> None:
    Scraper(config, scrape_mode).run()


if __name__ == "__main__":
    app()
