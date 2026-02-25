.PHONY: install dev lint format test clean docker-build docker-up

install:
	uv pip install -e .

dev:
	uv pip install -e ".[dev]"

lint:
	ruff check toolshield/ agentrisk/

format:
	ruff format toolshield/ agentrisk/

test:
	pytest tests/ -v

clean:
	rm -rf build/ dist/ *.egg-info .ruff_cache .pytest_cache __pycache__
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

docker-build:
	docker build -f docker/Dockerfile -t toolshield:latest .

docker-up:
	docker compose -f docker/docker-compose.yml up -d
