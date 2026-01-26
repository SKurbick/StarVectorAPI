@PHONY: up_local down up_dev down_dev

up_local:
	docker compose -f docker-compose-local-dev.yaml up -d && python3 main.py
down:
	docker compose -f docker-compose-local-dev.yaml down --remove-orphans

up_dev:
	docker compose -f docker-compose-for-front.yaml up -d

down_dev:
	docker compose -f docker-compose-for-front.yaml down --remove-orphans