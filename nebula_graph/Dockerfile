# Nebula-Graph Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . .

ENV PYTHONUNBUFFERED=1

# Entry point for the Graph DB Demo
CMD ["python", "-m", "nebula_graph.main"]
