# Hyperion-Stream Dockerfile
FROM python:3.11-slim

WORKDIR /app

# No external dependencies for this project, but we keep the structure standard
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Environment variables
ENV PYTHONUNBUFFERED=1

# Expose TCP port
EXPOSE 9090

# Default command
CMD ["python", "-m", "hyperion_stream.main", "--port", "9090"]
