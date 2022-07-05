import concurrent.futures
import json
import os
from urllib.parse import urlparse

import html2text
import requests
import yaml
from bs4 import BeautifulSoup
from dateutil.parser import parse as date_parse
from loguru import logger
from models import Episode, Person, Sponsor


config = {}

# Root dir where all the scraped data should to saved to.
# The data save to this dir follows the directory structure of the Hugo files relative
# to the root of the repo.
# Could be set via env variable to use the Hugo root directory.
# Any files that already exist in this directory will not be overwritten.
DATA_ROOT_DIR = os.getenv("DATA_DIR", "./data")


# Hold global data scraped from the `/guests` page (page with a list of all the guests 
# that appeared on the show e.g. https://coder.show/guests).
# The keys in this dict are the base url of each show (e.g. "https://coder.show"), and
# the keys of the "show" dict are usernames of the guests (e.g. "alexktz")
SHOW_GUESTS = {}


# The purpose of these following globals is to hold references (sometimes with data) to 
# entities that are referenced in a show episode. These are used to scrape and/or create
# the data json files after the episode files been created.
SHOW_SPONSOR_DATA = {}  # JSON filename as key (e.g. "linode.com-lup.json")
SHOW_HOSTS_URLS = set()  # Set of hosts' page urls (e.g. https://coder.show/host/chrislas)
SHOW_GUESTS_URLS = set() # Same as above, but for guests


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
        makedirs_safe(output_dir)

        # RANT: What kind of API doesn't give the episode number?!
        episode_number = int(api_episode["url"].split("/")[-1])
        episode_number_padded = f"{episode_number:03}"

        output_file = f"{output_dir}/{episode_number}.md"

        if os.path.isfile(output_file):
            logger.info(f"Skipping saving `{output_file}` as it already exists")
            return

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

        save_file(output_file, episode.get_hugo_md_file_content())

    except Exception as e:
        logger.exception("Failed to create an episode from url!\n"
                         f"episode_url: {api_episode.get('url')}")

def save_file(file_path, content, mode="w"):
    if os.path.exists(file_path):
        logger.warning(f"File `{file_path}` already exists. Will not overwrite!")
        return False
    
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
            SHOW_HOSTS_URLS.add(host_page_url)
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
            SHOW_GUESTS_URLS.add(guest_page_url)
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
            if sponsor_a and not SHOW_SPONSOR_DATA.get(filename):
                SHOW_SPONSOR_DATA.update({
                    filename: Sponsor(
                        shortname=shortname,
                        name=sponsor_a.find("header").text.strip(),
                        description=sponsor_a.find("p").text.strip(),
                        link=sl
                    ).dict()
                })
        except Exception as e:
            logger.exception("Failed to collect/parse sponsor data!\n"
                             f"  show: {show}\n"
                             f"  ep: {ep}")

    return sponsors


def save_json_file(filename, json_obj, dest_dir):
    makedirs_safe(dest_dir)

    file_path = os.path.join(dest_dir, filename)
    save_file(file_path, json.dumps(json_obj, indent=4))


def get_username_from_url(url):
    """
    Get the last path part of the url which is the username for the hosts and guests
    """
    username = urlparse(url).path.split("/")[-1]

    # Replace username if found in usernames_map
    usernames_map = config.get("usernames_map")
    if usernames_map:
        username = usernames_map.get(
            username, # get by the key that should be replaced
            username) # default to the key if not found


    return username


def create_host_or_guest(url, p_type):
    try:
        valid_p_types = {"host", "guest"}
        assert p_type in valid_p_types, f"p_type param must be one of {valid_p_types}"

        page_soup = BeautifulSoup(requests.get(url).content, "html.parser")
        
        username = get_username_from_url(url)  


        # From guests list page. Need this because sometimes the single guest page
        # is missing info (e.g. all self-hosted guests)
        show_url = url.split("/guests")[0]
        guest_data = SHOW_GUESTS.get(show_url, {}).get(username, {})  

        name = parse_name(page_soup, username, guest_data)
        
        dirname = f"{p_type}s"
        filename = save_avatar_img(dirname, page_soup, username, guest_data)

        # Get social links

        homepage = None
        twitter = None
        linkedin = None
        instagram = None
        gplus = None
        youtube = None
        nav = page_soup.find("nav", class_="links")
        if nav:
            links = nav.find_all("a")
                
            # NOTE: This will work only if none of the links are shortened urls
            for link in links:
                href = link.get("href").lower()
                if "Website" in link.text:
                    homepage = href
                elif "twitter" in href:
                    twitter = href
                elif "linkedin" in href:
                    linkedin = href
                elif "instagram" in href:
                    instagram = href
                elif "google" in href:
                    gplus = href
                elif "youtube" in href:
                    youtube = href
        
        bio = ""
        _bio = page_soup.find("section")
        if _bio:
            bio = _bio.text.strip()

        person = Person(
            type=p_type,
            username=username,
            name=name,
            bio=bio,
            avatar=f"/images/{dirname}/{filename}" if filename else None,
            homepage=homepage,
            twitter=twitter,
            linkedin=linkedin,
            instagram=instagram,
            gplus=gplus,
            youtube=youtube
        )

        hosts_dir = os.path.join(DATA_ROOT_DIR, "data", dirname)
        save_json_file(f"{username}.json", person.dict(), hosts_dir)
    except Exception as e:
        logger.exception("Failed to create/save a new host/guest file!\n"
                         f"  url: {url}")

def save_avatar_img(dirname, page_soup, username, guest_data):
    """Returns the `filename` if all is successfully downloaded, None otherwise"""
    try:
        avatar_url = get_avatar_url(page_soup, guest_data)
            
        if avatar_url:
            avatars_dir = os.path.join(DATA_ROOT_DIR, "static", "images", dirname)
            makedirs_safe(avatars_dir)

            filename = f"{username}.jpg"
            avatar_file = os.path.join(avatars_dir, filename)

            resp = requests.get(avatar_url)
            resp.raise_for_status()

            save_file(avatar_file, resp.content, mode="wb")

            return filename
    except Exception as e:
        logger.exception("Failed to save avatar!\n"
                         f"  username: {username}")


def get_avatar_url(page_soup, guest_data):
    avatar_url = None
    if guest_data:
        avatar_url = guest_data.get("avatar")
    else:
        avatar_div = page_soup.find("div", class_="hero-avatar")
        if avatar_div:
            avatar_url = avatar_div.find("img").get("src")
    return avatar_url


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
    logger.success(">>> Finished collecting all episode page urls") 

    # Scrape each page for data
    futures = []
    for show, show_episodes in JB_DATA.items():
        for ep, ep_data in show_episodes.items():
            futures.append(executor.submit(
                jb_get_ep_page_content, ep_data["jb_url"], ep_data, show, ep))

    for future in concurrent.futures.as_completed(futures):
        page_content, ep_data, show, ep = future.result()
        jb_populate_direct_links_for_episode(page_content, ep_data, show, ep)

    logger.success(">>> Finished scraping data from jupiterbroadcasting.com ✓")

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

    page_soup = BeautifulSoup(requests.get(
        show_base_url).content, "html.parser")
    pages_span = page_soup.find("span", class_="pages")
    if pages_span:
        last_page = pages_span.text.split(" ")[-1]
        last_page = int(last_page)
    else:
        last_page = 1  # Just one page

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


def scrape_hosts_guests_and_sponsors(shows, executor):
    output_dir = os.path.join(DATA_ROOT_DIR, "data", "sponsors")
    makedirs_safe(output_dir)
    
    scrape_show_guests_page(shows)  # into the SHOW_GUESTS global variable

    futures = []
    
    # Sponsors:
    for filename, sponsor in SHOW_SPONSOR_DATA.items():
        futures.append(executor.submit(
            save_json_file, filename, sponsor, output_dir))

    # Hosts:
    for url in SHOW_HOSTS_URLS:
        futures.append(executor.submit(create_host_or_guest, url, "host"))
    # Make sure all host files are saved
    for future in concurrent.futures.as_completed(futures):
        future.result()

    # Guests:
    for url in SHOW_GUESTS_URLS:
        futures.append(executor.submit(create_host_or_guest, url, "guest"))

    # Drain all threads
    for future in concurrent.futures.as_completed(futures):
        future.result()


def scrape_show_guests_page(shows):
    # no need to do thread since there's only a handful number of shows
    for show_slug, show_data in shows.items():
        all_guests_url = f"{show_data['fireside_url']}/guests"
        guests_soup = BeautifulSoup(requests.get(all_guests_url).content, "html.parser")
        links = guests_soup.find("ul", class_="show-guests").find_all("a")

        for l in links:
            url = l.get("href")
            username = url.rstrip("/").split("/")[-1]
            name = l.find("h5").text.strip()
            avatar_sm = l.find("img").get("src").split("?")[0]
            avatar = avatar_sm.replace("_small.jpg", ".jpg")

            this_show_guests = SHOW_GUESTS.get(show_data['fireside_url'], {})
            this_show_guests.update({
                username: {
                    "url": url,
                    "username": username,
                    "name": name,
                    "avatar_sm": avatar_sm,
                    "avatar": avatar
                }
            })
            SHOW_GUESTS.update({show_data['fireside_url']: this_show_guests})

def scrape_episodes_from_fireside(shows, executor):
    logger.info(">>> Scraping data from Fireside...")

    futures = []
    for show_slug, show_config in shows.items():
        # Use same structure as in the root project for easy copy over
        output_dir = os.path.join(
            DATA_ROOT_DIR, "content", "show", show_slug)
        makedirs_safe(output_dir)

        api_data = requests.get(
            show_config['fireside_url'] + "/json").json()

        for idx, api_episode in enumerate(api_data["items"]):
            futures.append(executor.submit(
                create_episode, api_episode, show_config,
                show_slug, output_dir
            ))

        # Drain to get exceptions. This is important in order to collect all the
        # MISSING_* globals first before proceeding
    for future in concurrent.futures.as_completed(futures):
        future.result()
    logger.success(">>> Finished scraping from Fireside ✓")


def main():
    global config
    with open("config.yml") as f:
        config = yaml.load(f, Loader=yaml.SafeLoader)
        shows = config['shows']

    with concurrent.futures.ThreadPoolExecutor() as executor:
        # Must be first. Here the JB_DATA global is populated
        scrape_data_from_jb(shows, executor)

        # save to a json file - this might be useful for files migrations
        jb_file = os.path.join(DATA_ROOT_DIR, "jb_all_shows_links.json")

        with open(jb_file, "w") as f:
            f.write(json.dumps(JB_DATA, indent=2))

        scrape_episodes_from_fireside(shows, executor)

        # Must come after scrape_episodes_from_fireside where the the globals: 
        # `SHOW_SPONSOR_DATA`, `SHOW_HOSTS_URLS`, and `SHOW_GUESTS_URLS` are populated
        scrape_hosts_guests_and_sponsors(shows, executor)


if __name__ == "__main__":
    logger.info("🚀🚀🚀 SCRAPER STARTED! 🚀🚀🚀")
    main()
    logger.success("🔥🔥🔥 ALL DONE :) 🔥🔥🔥\n\n")
    exit(0)
