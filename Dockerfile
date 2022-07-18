FROM python:3.10-alpine

ENV PIPENV_VENV_IN_PROJECT=1

WORKDIR /scraper
COPY . .
RUN pip install pipenv
RUN pipenv sync
RUN mkdir -p /data && chown -R 1000:1000 ./scraper.py .venv/ /data

USER 1000
ENTRYPOINT [ "pipenv", "run" ]
CMD [ "./scraper.py" ]
