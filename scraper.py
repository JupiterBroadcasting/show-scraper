#!/usr/bin/env python3

import concurrent.futures
import json
import os
import sys
from typing import Dict, List, Literal
from urllib.error import HTTPError
from urllib.parse import urlparse

import html2text
import requests
import yaml
from bs4 import BeautifulSoup, ResultSet
from loguru import logger
from models import Episode, Person, Sponsor
from models.person import PersonType


config = {}


# Limit scraping only the latest episodes of the show (executes the script much faster!)
# Used with GitHub Actions to run on a daily schedule and scrape the latest episodes.
IS_LATEST_ONLY = bool(os.getenv("LATEST_ONLY", False))
LATEST_ONLY_EP_LIMIT = 1

# Root dir where all the scraped data should to saved to.
# The data save to this dir follows the directory structure of the Hugo files relative
# to the root of the repo.
# Could be set via env variable to use the Hugo root directory.
# Any files that already exist in this directory will not be overwritten.
DATA_ROOT_DIR = os.getenv("DATA_DIR", "./data")


# The sponsors' data is collected into this global when episode files are scraped.
# This data is saved to files files after the episode files have been created.
SPONSORS: Dict[str, Sponsor] = {}  # JSON filename as key (e.g. "linode.com-lup.json")


# Global that holds scraped show episodes data from jupiterbroadcasting.com.
# The data is links to different types episode medium files (mp3, youtube, ogg, video,
#  etc.) - whatever is available on the episode page under the "Direct Download:" header 
#
# The structure of this is:
# {
#     "coderradio": {   # <-- `show_slug`` as defined in config.yml
#         "123": {   # <-- ep number
#             "youtube_link": "https://www.youtube.com/watch?v=98Mh0BP__gE",
#             ...
#         }
#     },
#     "show_slug_2": { ... }
# }
JB_DATA = {}

CHAPTERS_URL_TPL = "https://feeds.fireside.fm/{show}/json/episodes/{ep_id}/chapters"


def makedirs_safe(directory):
    try:
        os.makedirs(directory)
    except FileExistsError:
        pass


def get_list(soup: BeautifulSoup,
             pre_title: str,
             find_tag: str = "p",
             sibling_tag: str = "ul"):
    """
    Blocks of links are preceded by a find_tag (`p` default) saying what it is.
    """
    pre_element = soup.find(find_tag, string=pre_title)
    if pre_element is None:
        return None
    return pre_element.find_next_sibling(sibling_tag)


def seconds_2_hhmmss_str(seconds: str | int) -> str:
    seconds = int(seconds)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02}"


def get_plain_title(title: str) -> str:
    """
    Get just the show title, without any numbering etc
    """
    # Remove number before colon
    title = title.split(":", 1)[-1]

    # Remove data after the pipe
    title = title.rsplit("|", 1)[0]

    # Strip any stray spaces
    return title.strip()


def create_episode(api_episode,
                   show_config,
                   show_slug: str,
                   output_dir: str):
    try:
        # RANT: What kind of API doesn't give the episode number?!
        episode_number = int(api_episode["url"].split("/")[-1])
        episode_number_padded = f"{episode_number:04}"

        episode_guid = api_episode["id"]

        output_file = f"{output_dir}/{episode_number_padded}.md"

        if not IS_LATEST_ONLY and os.path.isfile(output_file):
            # Overwrite when IS_LATEST_ONLY mode is true
            # Because the episode is published on JB website after fireside
            logger.warning(f"Skipping saving `{output_file}` as it already exists")
            return

        podcast_chapters = get_podcast_chapters(api_episode, show_config)

        publish_date = api_episode['date_published']

        api_soup = BeautifulSoup(api_episode["content_html"], "html.parser")
        page_soup = BeautifulSoup(requests.get(
            api_episode["url"]).content, "html.parser")

        blurb = api_episode["summary"]

        sponsors = parse_sponsors(
            api_soup, page_soup, show_config["acronym"], episode_number)

        links_list = get_list(api_soup, "Links:") or get_list(api_soup, "Episode Links:")
        links = html2text.html2text(str(links_list)) if links_list else None

        tags = []
        for link in page_soup.find_all("a", class_="tag"):
            _tag = link.get_text().strip()
            # escape inner quotes (occurs in coderradio 434)
            _tag = _tag.replace("\"", "\\\"")
            tags.append(_tag)

        tags = sorted(tags)

        hosts = parse_hosts_in_ep(page_soup, show_config, episode_number)
        guests = parse_guests_in_ep(page_soup, show_config, episode_number)

        show_attachment = api_episode["attachments"][0]

        jb_ep_data = JB_DATA.get(show_slug, {}).get(episode_number, {})
        # logger.debug(f"{episode_number} jb_ep_data: {jb_ep_data}")
        jb_url = jb_ep_data.get("jb_url")
        if jb_url:
            jb_url = urlparse(jb_url).path


        episode = Episode(
                show_slug=show_slug,
                show_name=show_config["name"],
                episode=episode_number,
                episode_padded=episode_number_padded,
                episode_guid=episode_guid,
                title=get_plain_title(api_episode["title"]),
                description=blurb,
                date=publish_date,
                tags=tags,
                hosts=hosts,
                guests=guests,
                sponsors=sponsors,
                podcast_duration=seconds_2_hhmmss_str(show_attachment['duration_in_seconds']),
                podcast_file=show_attachment["url"],
                podcast_bytes=show_attachment.get("size_in_bytes"),
                podcast_chapters=podcast_chapters,
                podcast_alt_file=jb_ep_data.get("mp3_audio"),
                podcast_ogg_file=jb_ep_data.get("ogg_audio"),
                video_file=jb_ep_data.get("video"),
                video_hd_file=jb_ep_data.get("hd_video"),
                video_mobile_file=jb_ep_data.get("mobile_video"),
                youtube_link=jb_ep_data.get("youtube"),
                jb_url=jb_url,
                fireside_url=urlparse(api_episode["url"]).path,
                episode_links=links
            )        

        save_file(output_file, episode.get_hugo_md_file_content(), overwrite=IS_LATEST_ONLY)

    except Exception as e:
        logger.exception("Failed to create an episode from url!\n"
                         f"episode_url: {api_episode.get('url')}")

def get_podcast_chapters(api_episode, show_config):
    try:
        chapters_url = CHAPTERS_URL_TPL.format(
                show=show_config["fireside_slug"],
                ep_id=api_episode["id"])

        resp = requests.get(chapters_url)
        resp.raise_for_status()

        return resp.json()
    except requests.HTTPError:
        # No chapters
        pass

def save_file(file_path, content, mode="w", overwrite=False):
    if not overwrite and os.path.exists(file_path):
        logger.warning(f"Skipping saving `{file_path}` as it already exists")
        return False
    
    makedirs_safe(os.path.dirname(file_path))
    with open(file_path, mode) as f:
        f.write(content)
    logger.info(f"Saved file: {file_path}")
    return True

def parse_hosts_in_ep(page_soup: BeautifulSoup, show_config, ep):
    show = show_config["acronym"]
    base_url = show_config["fireside_url"]

    episode_hosts = []

    # assumes the hosts are ALWAYS the first <ul> and guests are in the second one
    hosts_links = page_soup.find("ul", class_="episode-hosts").find_all("a")

    # hosts_links = page_soup.select(".episode-hosts ul:first-child a")
    for link in hosts_links:
        try:
            host_page_url = base_url + link.get("href")
            episode_hosts.append(get_username_from_url(host_page_url))
        except Exception as e:
            logger.exception(f"Failed to parse HOST for link href!\n"
                             f"  show: {show}\n"
                             f"  ep: {ep}\n"
                             f"  href: {link.get('hrerf')}")
    return episode_hosts


def parse_guests_in_ep(page_soup, show_config, ep):
    show = show_config["acronym"]
    base_url = show_config["fireside_url"]

    episode_guests = []

    # assumes the hosts are ALWAYS the first <ul> and guests are in the second one
    # <- this would always be the hosts list
    hosts_list = page_soup.find("ul", class_="episode-hosts")
    # look for the NEXT `ul.episode-hosts`, that should be the guests list (might not exist)
    guests_list = hosts_list.find_next("ul", class_="episode-hosts")
    if not guests_list:
        return episode_guests
    guests_links = guests_list.find_all("a")
    for link in guests_links:
        try:
            guest_page_url = base_url + link.get("href")
            episode_guests.append(get_username_from_url(guest_page_url))
        except Exception as e:
            logger.exception(f"Failed to parse GUEST for link href!\n"
                             f"  show: {show}\n"
                             f"  ep: {ep}\n"
                             f"  href: {link.get('hrerf')}")

    return episode_guests


def parse_sponsors(api_soup, page_soup, show, ep):
    # Get only the links of all the sponsors
    sponsors_ul = get_list(api_soup, "Sponsored By:")
    if not sponsors_ul:
        logger.warning("No sponsors found for this episode.\n"
                       f"  show: {show}\n"
                       f"  ep: {ep}")
        return []

    sponsors_links = [a["href"]
                      for a in sponsors_ul.select('li > a:first-child')]

    sponsors = []
    for sl in sponsors_links:
        try:
            # Very ugly but works. The goal is to get the hostname of the sponsor
            # link without the subdomain. It would fail on tlds like "co.uk". but I
            # don't think JB had any sponsors like that so it's fine.
            sponsor_slug = ".".join(urlparse(sl).hostname.split(".")[-2:])
            shortname = f"{sponsor_slug}-{show}".lower()
            sponsors.append(shortname)

            filename = f"{shortname}.json"

            # Find the <a> element on the page with the link
            sponsor_a = page_soup.find(
                "div", class_="episode-sponsors").find("a", attrs={"href": sl})
            if sponsor_a and not SPONSORS.get(filename):
                SPONSORS.update({
                    filename: Sponsor(
                        shortname=shortname,
                        name=sponsor_a.find("header").text.strip(),
                        description=sponsor_a.find("p").text.strip(),
                        link=sl
                    )
                })
        except Exception as e:
            logger.exception("Failed to collect/parse sponsor data!\n"
                             f"  show: {show}\n"
                             f"  ep: {ep}")

    return sponsors


def save_json_file(filename, json_obj, dest_dir, overwrite=False):
    file_path = os.path.join(dest_dir, filename)
    save_file(file_path, json.dumps(json_obj, indent=4), overwrite=overwrite)


def get_username_from_url(url):
    """
    Get the last path part of the url which is the username for the hosts and guests.
    Replace it using the `username_map` from config.
    """
    username = urlparse(url).path.split("/")[-1]

    # Replace username if found in usernames_map
    usernames_map = config.get("usernames_map")
    if usernames_map:
        username = usernames_map.get(
            username, # get by the key that should be replaced
            username) # default to the key if not found


    return username


def save_avatar_img(img_url: str, username: str, is_small=False) -> str:
    """Save the avatar image only if it doesn't exist.

    Return the file path relative to the `static` folder.
    For example: "images/people/chris.jpg"
    """
    try:
        relative_filepath = get_avatar_relative_path(username, is_small)
        full_filepath = os.path.join(DATA_ROOT_DIR, "static", relative_filepath)

        # Check if file exist BEFORE the request. This is more efficient as it saves 
        # time and bandwidth
        if os.path.exists(full_filepath):
            logger.warning(f"Skipping saving `{full_filepath}` as it already exists")
            return relative_filepath
        
        resp = requests.get(img_url)
        resp.raise_for_status()

        save_file(full_filepath, resp.content, mode="wb")
        return relative_filepath
    except Exception:
        logger.exception("Failed to save avatar!\n"
                         f"  img_url: {img_url}"
                         f"  username: {username}") 


def get_avatar_relative_path(username, is_small=False):
    # Assume all images are JPG.
    # Might need to use `python-magic` lib to get the actual mime-type and append 
    # appropriate file extension.
    filename_suffix = "_small.jpg" if is_small else ".jpg"
    filename = username + filename_suffix
    relative_filepath = os.path.join("images", "people", filename)
    return relative_filepath


def parse_name(page_soup, username, guest_data):
    # Fallback name to be to username
    name = username

    name_h1 = page_soup.find("h1")
    if name_h1:
        name = name_h1.text.strip()
    elif guest_data: 
        name = guest_data.get("name", username)
    return name
     

def scrape_data_from_jb(shows, executor):
    logger.info(">>> Scraping data from jupiterbroadcasting.com...")

    # Collect all links for episode page of each show into JB_DATA
    for show_slug, show_config in shows.items():
        show_base_url = show_config["jb_url"]
        jb_populate_episodes_urls(show_slug, show_base_url)
    logger.success(">>> Finished collecting urls of episode pages") 

    logger.info(">>> Scraping data from each episode page...")
    # Scrape each page for data
    futures = []
    for show, show_episodes in JB_DATA.items():
        for ep, ep_data in show_episodes.items():
            futures.append(executor.submit(
                jb_get_ep_page_content, ep_data["jb_url"], ep_data, show, ep))

    for future in concurrent.futures.as_completed(futures):
        page_content, ep_data, show, ep = future.result()
        jb_populate_direct_links_for_episode(page_content, ep_data, show, ep)

    # save to a json file - this might be useful for files migrations
    # save_json_file("jb_all_shows_links.json", JB_DATA, DATA_ROOT_DIR)
    logger.success(">>> Finished scraping data from jupiterbroadcasting.com")

def jb_get_ep_page_content(page_url, ep_data, show, ep):
    resp = requests.get(page_url)
    return resp.content, ep_data, show, ep

def jb_populate_direct_links_for_episode(ep_page_content, ep_data, show, ep):
    try:
        ep_soup = BeautifulSoup(ep_page_content, "html.parser")
        dd_div = ep_soup.find("div", attrs={"id": "direct-downloads"})
        if dd_div:
            dl_links = dd_div.find_all("a")
        else:
            # older episodes have different structure.
            p_links = get_list(ep_soup, "Direct Download:", "h3", "p")
            if p_links:
                dl_links = p_links.find_all("a")
            else:
                logger.warning(
                    "Failed to find Direct Download links for the episode.\n"
                    f"  show: {show} \n"
                    f"  ep: {ep}")
                return

        for dl_link in dl_links:
            url = dl_link.get("href").strip("\\\"")
            slug = dl_link.text.lower().replace(" ", "_")
            ep_data.update({
                slug: url
            })
    except Exception as e:
        logger.exception(
            "Failed to parse direct links for episode.\n"
            f"  show: {show} \n"
            f"  ep: {ep}")


def jb_populate_episodes_urls(show_slug, show_base_url):
    show_data = {}
    JB_DATA.update({show_slug: show_data})

    last_page = jb_get_last_page_of_show(show_base_url)

    futures = []

    with concurrent.futures.ThreadPoolExecutor() as executor:
        for page in range(1, last_page+1):
            page_url = f"{show_base_url}/page/{page}/"
            futures.append(executor.submit(requests.get, page_url))

    for future in concurrent.futures.as_completed(futures):
        resp = future.result()
        page_soup = BeautifulSoup(resp.content, "html.parser")
        videoitems = page_soup.find_all("div", class_="videoitem")
        for idx, item in enumerate(videoitems):
            if IS_LATEST_ONLY and idx >= LATEST_ONLY_EP_LIMIT:
                logger.debug(f"Limiting scraping to only {LATEST_ONLY_EP_LIMIT} most"
                            " recent episodes")
                break


            try:
                link = item.find("a")
                link_href = link.get("href")
                ep_num = link.get("title").split(" ")[-1]

                if ep_num == "LU1":
                    # LUP edge case for ep 1
                    ep_num = 1
                if link.get("title") == "Goodbye from Linux Action News":
                    # LAN edge case. This episode is between ep152 and 153, hence it
                    # shall be officially titled as episode 152.5 for now forth
                    # (hopefully having floaty number won't brake things 😛)

                    # TODO create the episode file for this, cuz it's not in Fireside
                    ep_num = 152.5
                # Some Coder exceptions
                if link.get("title") == "Say My Functional Name | Coder Radio":
                    ep_num = 343
                if link.get("title") == "New Show! | Coder Radio":
                    ep_num = 0
                else:
                    ep_num = int(ep_num)

                show_data.update({ep_num: {
                    "jb_url": link_href
                }})
            except Exception as e:
                logger.exception(
                    "Failed to get episode page link and number from JB site.\n"
                    f"  show: {show_slug}\n"
                    f"  page: {page}\n"
                    f"  ep_idx: {idx}\n"
                    f"  html: {item.string}")

def jb_get_last_page_of_show(show_base_url):
    if IS_LATEST_ONLY:
        logger.debug(f"Force only scraping of the most recent page")
        # Scrape only the most recent page
        return 1

    page_soup = BeautifulSoup(requests.get(
        show_base_url).content, "html.parser")
    pages_span = page_soup.find("span", class_="pages")
    if pages_span:
        last_page = pages_span.text.split(" ")[-1]
        last_page = int(last_page)
    else:
        last_page = 1  # Just one page
    return last_page


def scrape_hosts_and_guests(shows, executor):
    logger.info(">>> Scraping hosts and guests from Fireside...")
    people_dir = os.path.join(DATA_ROOT_DIR, "data", "people")

    guests = scrape_show_guests(shows, executor)
    hosts = scrape_show_hosts(shows, executor)
    people = guests | hosts  # combine the two dicts (hosts data overrides guests)


    # Save json files asyncronously
    futures = []
    for username, person in people.items():
        futures.append(executor.submit(save_json_file, f"{username}.json", person.dict(), people_dir))

    # Drain all threads
    for future in concurrent.futures.as_completed(futures):
        future.result()
    logger.success(">>> Finished scraping hosts and guests")


def scrape_show_hosts(shows: Dict, executor) -> Dict[str, Person]:
    show_hosts = {}
    for show_data in shows.values():
        show_fireside_url = show_data['fireside_url']
        all_hosts_url = f"{show_fireside_url}/hosts"
        hosts_soup = BeautifulSoup(requests.get(all_hosts_url).content, "html.parser")
        
        for host_soup in hosts_soup.find_all("div", class_="host"):
            host_info_soup = host_soup.find("div", class_="host-info")
            
            host_link = host_info_soup.find("h3").find("a")
            name = host_link.text.strip()
            host_url = show_fireside_url + host_link.get("href")
            username = get_username_from_url(host_url)

            bio = host_info_soup.find("p").text
            
            links = host_info_soup.find("ul", class_="host-links").find_all("a")
            links_data = parse_social_links(links)

            avatar_small_url = host_soup.find("div", class_="host-avatar").find("img").get("src")
            avatar_url = avatar_small_url.replace("_small.jpg", ".jpg")

            avatar_small = save_avatar_img(avatar_small_url, username, is_small=True)
            avatar = save_avatar_img(avatar_url, username)

            append_person_to_dict("host", show_hosts, username, show_data["acronym"],
                                  name=name,
                                  avatar="/"+avatar,
                                  avatar_small="/"+avatar_small,
                                  bio=bio,
                                  **links_data)
            

    return show_hosts

def scrape_show_guests(shows: Dict, executor) -> Dict[str, Person]:
    """Return dict of Person by username
    """

    show_guests = {}  # username as key

    # no need to do thread since there's only a handful number of shows
    for show_data in shows.values():
        show_fireside_url = show_data['fireside_url']
        all_guests_url = f"{show_fireside_url}/guests"
        guests_soup = BeautifulSoup(requests.get(all_guests_url).content, "html.parser")
        links = guests_soup.find("ul", class_="show-guests").find_all("a")

        all_urls = [show_fireside_url + a.get("href") for a in links]
        guest_pages = get_pages_content_threaded(all_urls, executor)

        for l in links:
            url = show_fireside_url + l.get("href")
            username = get_username_from_url(url)
            name = l.find("h5").text.strip()
            avatar_small_url = l.find("img").get("src").split("?")[0]
            avatar_url = avatar_small_url.replace("_small.jpg", ".jpg")

            avatar_small = save_avatar_img(avatar_small_url, username, is_small=True)
            avatar = save_avatar_img(avatar_url, username)

            html_page = guest_pages.get(url)
            page_data = parse_person_page(html_page)

            append_person_to_dict("guest", show_guests, username, show_data["acronym"],
                                  name=name,
                                  avatar="/"+avatar,
                                  avatar_small="/"+avatar_small,
                                  **page_data)

    return show_guests


def append_person_to_dict(p_type: PersonType, the_dict: dict, username, show_acr: str, **data):
    new = Person(type=p_type, username=username, **data)
    existing = the_dict.get(username)
    if existing and existing.dict() != new.dict() and not IS_LATEST_ONLY:
        # If different, save as an alternative version
        the_dict[f"__{username}_{show_acr}"] = new
    else:
        the_dict[username] = new


def parse_person_page(html_page):
    if not html_page:
        return {}

    page_soup = BeautifulSoup(html_page, "html.parser")
    page_data = {}

            # Parse bio
    bio = page_soup.find("section")
    if bio:
        page_data["bio"] = bio.text.strip()

            # Parse social links
    nav = page_soup.find("nav", class_="links")
    if nav:
        links = nav.find_all("a")
        page_data = {**page_data, **parse_social_links(links)}
        
    return page_data


def parse_social_links(links: ResultSet):
    result = {}
    for link in links:
        href = link.get("href").lower()
        label = link.text.lower()
        if "website" in label:
            result["homepage"] = href
        elif "twitter" in label:
            result["twitter"] = href
        elif "linkedin" in label:
            result["linkedin"] = href
        elif "instagram" in label:
            result["instagram"] = href
        elif "google" in label:
            result["gplus"] = href
        elif "youtube" in label:
            result["youtube"] = href

    return result


def get_pages_content_threaded(urls: List[str], executor) -> Dict[str, str]:
    result = {}  # by request url as key

    futures = []
    for url in urls:
        futures.append(executor.submit(requests.get, url))
    
    for f in concurrent.futures.as_completed(futures):
        resp: requests.Response = f.result()
        if not resp.ok:
            logger.error("GET Request failed!\n"
            f" url: {resp.request.url}\n"
            f" status code: {resp.status_code}\n"
            f" msg: {resp.reason}")
            continue

        result[resp.request.url] = resp.content
    
    return result


def scrape_episodes_from_fireside(shows, executor):
    logger.info(">>> Scraping episodes from Fireside...")

    futures = []
    for show_slug, show_config in shows.items():
        # Use same structure as in the root project for easy copy over
        output_dir = os.path.join(
            DATA_ROOT_DIR, "content", "show", show_slug)

        api_data = requests.get(
            show_config['fireside_url'] + "/json").json()

        for idx, api_episode in enumerate(api_data["items"]):

            if IS_LATEST_ONLY and idx >= LATEST_ONLY_EP_LIMIT:
                logger.debug(f"Limiting scraping to only {LATEST_ONLY_EP_LIMIT} most"
                            " recent episodes")
                break

            futures.append(executor.submit(
                create_episode, api_episode, show_config,
                show_slug, output_dir
            ))

    # Drain to get exceptions. This is important in order to collect all the
    # MISSING_* globals first before proceeding
    for future in concurrent.futures.as_completed(futures):
        future.result()
    logger.success(">>> Finished scraping from episodes ✓")


def save_sponsors(executor):
    logger.info(">>> Saving the sponsors found in episodes from Fireside...")
    sponsors_dir = os.path.join(DATA_ROOT_DIR, "data", "sponsors")
    futures = []
    for filename, sponsor in SPONSORS.items():
        futures.append(executor.submit(
        save_json_file, filename, sponsor.dict(), sponsors_dir))

    # Drain all threads
    for future in concurrent.futures.as_completed(futures):
        future.result()
    logger.success(">>> Finished saving sponsors")


def main():
    global config
    with open("config.yml") as f:
        config = yaml.load(f, Loader=yaml.SafeLoader)
        shows = config['shows']

    with concurrent.futures.ThreadPoolExecutor() as executor:
        # Must be first. Here the JB_DATA global is populated
        scrape_data_from_jb(shows, executor)

        scrape_episodes_from_fireside(shows, executor)

        save_sponsors(executor)

        scrape_hosts_and_guests(shows, executor)


if __name__ == "__main__":
    LOG_LVL = int(os.getenv("LOG_LVL", 20))  # Defaults to INFO
    logger.remove()  # Remove default logger
    logger.add(sys.stderr, level=LOG_LVL)

    logger.info("🚀🚀🚀 SCRAPER STARTED! 🚀🚀🚀")
    main()
    logger.success("🔥🔥🔥 ALL DONE :) 🔥🔥🔥\n\n")
    exit(0)
