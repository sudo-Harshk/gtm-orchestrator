.PHONY: dev health logs

dev:
	docker compose up --build

health:
	curl http://localhost:8000/health

logs:
	docker compose logs -f
