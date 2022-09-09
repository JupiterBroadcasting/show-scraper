scrape: clean
	docker-compose up -d --build scraper && docker-compose logs --no-log-prefix -f

clean:
	-rm -r ./data
	-mkdir ./data

test:
	pytest --no-header -v