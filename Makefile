scrape: clean mkdir-data
	docker-compose up -d --build scraper && docker-compose logs --no-log-prefix -f

clean:
	-rm -r ./data
	-mkdir ./data
