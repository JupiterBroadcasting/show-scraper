# JupiterBroadcasting Show Scraper

 🚨**ATTENTION:**🚨

**Make commits into `main` with great caution, as this branch is used in "production" by the [jupiterbroadcasting.com GitHub Action](https://github.com/JupiterBroadcasting/jupiterbroadcasting.com/tree/main/.github/workflows/scrape.yml).**

---

Scraper written in python to convert episodes hosted on Fireside or jupiterbroadcasting.com (Wordpress) into Hugo files.

Originally based on [Self-Hosted show-notes scraper](https://github.com/selfhostedshow/show-notes/blob/main/scrape.py) 

## Data

All the scraped data is saved into the `./data` folder.

`config.yml` contains:

* `usernames_map` - Fireside to Hugo username translations
	
* `data_dont_override` - data filenames (sponsors or people) which shouldn't be overridden when scraping Fireside

## Run using Docker

```
make scrape
```

## Run without Docker


### Setup python venv

Install [pipenv](https://pipenv.pypa.io/en/latest/basics/):

```
pip3 install pipenv
```


Install all the dependencies

```
pipenv install -d
```

Activate your pipenv shell:

```
pipenv shell
```


### Run

Make sure you have activated the pipenv virtual environment, running `which python` should point to the binary inside the pipenv `venv` dir.


Run the script from the root dir:

```
python scraper.py
```

You can set these env variables:

- `LOG_LVL`: Integer severity value for the loguru library (see [this table](https://loguru.readthedocs.io/en/stable/api/logger.html#levels)). Defaults to 20 (INFO).
- `LATEST_ONLY`: Set to `true` to scrape only the latest episode of each show defined in `config.yml`. This mode is used for automatically scraping new episode with GitHub actions. Default mode is to scrape all episodes and all data.
- `DATA_DIR`: The location where all the scraped files would be saved to. Defaults to `./data`.


Example:

```
LOG_LVL=1 LATEST_ONLY=1 python scraper.py
```
