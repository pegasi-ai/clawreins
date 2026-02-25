FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml setup.py README.md ./
COPY toolshield/ toolshield/

RUN pip install --no-cache-dir .

ENTRYPOINT ["toolshield"]
