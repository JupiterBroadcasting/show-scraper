# JupiterBroadcasting Show Scraper

Scraper written in python to convert episodes hosted on Fireside or jupiterbroadcasting.com into Hugo files.


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

