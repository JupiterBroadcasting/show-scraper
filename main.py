#!/usr/bin/env python3

from concurrent.futures import ThreadPoolExecutor, as_completed
from email.utils import parsedate_to_datetime
from typing import Any, Dict, Optional

import requests
import typer
import yaml
from bs4 import BeautifulSoup, NavigableString, ResultSet, Tag
from loguru import logger
from pydantic import HttpUrl

from models import EpisodeLink, ScrapedEpisode, Show, Shows
from utils import capitalize_text


class Scraper:
    """
    The goal of this scraper is to collect a big picture of the JB episodes (archived and current shows). Mainly we care about media files, but other episode data:
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

    def __init__(self, config_file_path: str) -> None:
        self.shows = Shows(__root__={})

        with open(config_file_path) as f:
            self.config: Dict[str, Any] = yaml.load(f, Loader=yaml.SafeLoader)

    def run(self) -> None:
        logger.info("Start!")

        self.scrape_rss_feeds()

        self.scrape_jb_website()

        print(self.shows.json(exclude_none=True, indent=2))

    def _clear_broken_urls_in_episodes(self, show: Show):
        futures = []
        with ThreadPoolExecutor() as executor:
            for ep_num, ep_obj in show.episodes.items():
                f = executor.submit(self._clear_broken_urls, ep_obj)
                futures.append(f)

        # Drain all threads
        [f for f in as_completed(futures)]

    def _get_show_obj(self, show_slug: str) -> Show:
        show = self.shows[show_slug]
        if not show:
            # Create new show object
            show = Show(show_slug=show_slug, episodes={})
            self.shows[show_slug] = show
        return show

    def _jb_scrape_ep_pages(self, jb_show_url: HttpUrl) -> Dict[str, str]:
        # TODO
        return {}

    @staticmethod
    def _clear_broken_urls(ep: ScrapedEpisode):
        if ep.enclosure_url:
            resp = requests.head(ep.enclosure_url, allow_redirects=True)
            if not resp.ok:
                # Remove broken url
                ep.enclosure_url = None
                ep.enclosure_src = None

        if ep.chapters_url:
            resp = requests.head(ep.chapters_url, allow_redirects=True)
            if not resp.ok:
                # Remove broken url
                ep.chapters_url = None

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
            self._get_show_obj(show_slug)

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

    def scrape_rss_feeds(self) -> None:
        for show_slug, show_conf in self.config["shows"].items():
            show = self._get_show_obj(show_slug)

            rss_url: str = show_conf.get("rss_url")
            if not rss_url:
                continue

            resp = requests.get(rss_url)
            if not resp.ok:
                logger.error(
                    f"Request to {rss_url} failed! "
                    f"{resp.status_code}: {resp.reason}"
                )
                continue

            feed_bs = BeautifulSoup(resp.content, "lxml-xml")
            for item_bs in feed_bs.find_all("item"):
                link = item_bs.find("link").text
                ep = link.split("/")[-1]
                title = self._get_plain_title(item_bs.find("title").text)

                episode = show.episodes.get(ep)
                if not episode:
                    # Create new episode object
                    episode = ScrapedEpisode(
                        show_slug=show_slug, episode=ep, title=title
                    )
                    show.episodes[ep] = episode

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
                        episode.enclosure_url = _enclosure.get("url")
                        episode.enclosure_src = show_conf["rss_src"]

                if not episode.chapters_url:
                    _chapters = item_bs.find("podcast:chapters")
                    if _chapters:
                        episode.chapters_url = _chapters.get("url")

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

                            desc = (
                                li.contents[1].string if len(li.contents) == 2 else None
                            )
                            if desc:
                                desc = desc.removeprefix(" — ")  # &mdash;
                                desc = desc.replace("\r\n", "")
                                desc = desc.strip()

                            ep_link = EpisodeLink(
                                title=title, url=url, description=desc
                            )
                            episode.episode_links.append(ep_link)

                self._clear_broken_urls_in_episodes(show)


_DEFAULT_CONFIG_FILE = "config.yml"


def main(config_file: str = _DEFAULT_CONFIG_FILE):
    Scraper(config_file).run()


if __name__ == "__main__":
    typer.run(main)
