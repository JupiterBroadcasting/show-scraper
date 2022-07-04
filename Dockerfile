FROM python:3.10-alpine

RUN mkdir /data && chown -R 1000:1000 /data

WORKDIR /scraper
COPY . .
RUN chown 1000:1000 ./scraper.py
RUN pip install -r requirements.txt

USER 1000
CMD [ "python3", "scraper.py" ]