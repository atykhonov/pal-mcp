FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy source code and config
COPY pyproject.toml README.md ./
COPY src/ src/

# Install package
RUN pip install --no-cache-dir .

# Copy runtime files
COPY files/ files/

# Set environment variables
ENV PAL_SERVER_HOST=0.0.0.0
ENV PAL_SERVER_PORT=8090

EXPOSE 8090

# Run the server
CMD ["python", "-m", "pal"]
