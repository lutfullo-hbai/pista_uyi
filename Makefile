.PHONY: dev dev-bot dev-web test docker-build docker-up docker-down clean

dev:
	pip install -r requirements.txt
	python run.py

dev-bot:
	python run.py --bot-only

dev-web:
	python run.py --web-only

test:
	pytest tests/ -v --cov=. --cov-report=term-missing

docker-build:
	docker compose build

docker-up:
	docker compose up -d

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.pyc' -delete
