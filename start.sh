#!/bin/bash
# start.sh — Ejecuta migraciones y luego inicia la aplicación en Render
set -e

echo "=== Ejecutando migraciones de base de datos ==="
alembic upgrade head

echo "=== Iniciando servidor ==="
uvicorn app.main:app --host 0.0.0.0 --port $PORT
