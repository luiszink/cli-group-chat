# Dockerfile für Group Chat System
FROM python:3.11-slim

# Arbeitsverzeichnis erstellen
WORKDIR /app

# Gesamte Projektstruktur kopieren
COPY src/ ./src/
COPY docker/ ./docker/
COPY scripts/ ./scripts/

# Expose Ports
# 5555: Server TCP
# 6000-6010: Client UDP Ports
EXPOSE 5555
EXPOSE 6000-6010

# Standard-Kommando (wird von docker-compose überschrieben)
CMD ["python", "src/server.py", "5555"]
