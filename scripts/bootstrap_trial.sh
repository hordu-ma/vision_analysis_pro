#!/usr/bin/env bash
set -euo pipefail

if [[ ! -f .env ]]; then
  cp .env.example .env
fi

mkdir -p data models runs

docker compose up --build -d

echo "Trial environment started."
echo "Web: http://localhost:4173"
echo "API: http://localhost:8000"
