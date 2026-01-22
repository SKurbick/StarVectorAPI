@PHONY: up_local, down

up_local:
	docker compose -f docker-compose-local-dev.yaml up -d && python3 main.py
down:
	docker compose -f docker-compose-local-dev.yaml down --remove-orphans