import pytest
import yaml
import scraper
from scraper import get_username_from_url


@pytest.fixture
def config_data():
    with open("config.yml") as f:
        config = yaml.load(f, Loader=yaml.SafeLoader)
    return config

def test_matched_host_urls(config_data):
    # set global variable
    scraper.config = config_data

    # Linux Action News
    assert get_username_from_url("/hosts/drewdvore") == "drew-devore"

    # Coder
    assert get_username_from_url("/hosts/chrislas") == "chris"
    assert get_username_from_url("/hosts/wespayne") == "wes"
    
    # Extras
    assert get_username_from_url("/hosts/alexktz") == "alex"

    # Office Hours
    assert get_username_from_url("/hosts/brentgervais") == "brent"

def test_unmatched_host_urls(config_data):
    # set global variable
    scraper.config = config_data

    # Linux Action News
    assert get_username_from_url("/hosts/chris") == "chris"
    assert get_username_from_url("/hosts/joe") == "joe"
    assert get_username_from_url("/hosts/wes") == "wes"

    # Coder
    assert get_username_from_url("/hosts/michael") == "michael"

def test_matched_guests_urls(config_data):
    # set global variable
    scraper.config = config_data

    # Selfhosted
    assert get_username_from_url("/guests/alanpope") == "popey"

    # Linux Unplugged
    assert get_username_from_url("https://linuxunplugged.com/guests/martinwimpress") == "wimpy" 


def test_unmatched_guests_urls(config_data):
    # set global variable
    scraper.config = config_data

    # Selfhosted
    assert get_username_from_url("https://selfhosted.show/guests/jscar") == "jscar"
    assert get_username_from_url("https://selfhosted.show/guests/drewofdoom") == "drew-devore"

    # Linux Unplugged
    assert get_username_from_url("https://linuxunplugged.com/guests/christianschaller") == "christianschaller" 