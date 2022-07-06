# JupiterBroadcasting Show Scraper

**ATTENTION:**

**Make commits into the `main` with great caution, as this branch is used in "production" by the [jupiterbroadcasting.com GitHub Action](https://github.com/JupiterBroadcasting/jupiterbroadcasting.com/tree/main/.github/workflows/scrape.yml).**

---

Scraper written in python to convert episodes hosted on Fireside or jupiterbroadcasting.com into Hugo files.

Originally based on [Self-Hosted show-notes scraper](https://github.com/selfhostedshow/show-notes/blob/main/scrape.py) 


All the scraped data is saved into the `./data` folder.


## Run using Docker

```
make scrape
```

## Run without Docker


### Setup python venv

Create a python virtual environment:

```
python3 -m venv venv
```


Activate the venv:

```
source venv/bin/activate
```

or use any other `activate` file that would match your shell, for example if you're using `fish`:

```
source venv/bin/activate.fish
```

Then install the dependecies:

```
pip install -r requirements.txt
```


### Run

Make sure you have activated the virtual envirnoment, running `which python` should point to the binary inside the `venv` dir.


Run the script from the root dir:

```
python scraper.py
```

You can set these env variables:

- `LOG_LVL`: Integer severity value for the loguru library (see [this table](https://loguru.readthedocs.io/en/stable/api/logger.html#levels)). Defaults to 20 (INFO).
- `LATEST_ONLY`: Set to `1` to scrape only the latest episode of each show defined in `config.yml`. This mode is used for automatically scraping new episode with github actions. Default mode is to scrape all episodes and all data.
- `DATA_DIR`: The location where all the scraped files would be saved to. Defaults to `./data`.


Example:

```
LOG_LVL=1 LATEST_ONLY=1 python scraper.py
```

