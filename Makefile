scrape: clean
	docker-compose up -d --build scraper && docker-compose logs --no-log-prefix -f

clean:
	-rm -r ./data
	-mkdir ./data

# FIXME: make docker compatible in the future
test:
	python -m pytest -ra -v