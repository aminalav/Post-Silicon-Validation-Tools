# Backend image: builds the C++ extension and serves the API with seeded data.
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential cmake git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml CMakeLists.txt README.md ./
COPY cpp ./cpp
COPY sep ./sep
COPY specs ./specs

RUN pip install --upgrade pip && pip install .

# Seed the database on first boot, then serve.
ENV SEP_DB_URL=sqlite:////app/sep.db
EXPOSE 8000
CMD ["sh", "-c", "sep demo --db-url $SEP_DB_URL && sep serve --host 0.0.0.0 --port 8000"]
