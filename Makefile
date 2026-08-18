.PHONY: dev test

dev:
	docker compose up --build

test:
	docker compose run --rm backend pytest
