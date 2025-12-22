FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml README.md ./
RUN pip install --no-cache-dir .

# Copy source code
COPY src/ src/
COPY files/ files/
COPY prompts/ prompts/

# Set environment variables
ENV PAL_SERVER_HOST=0.0.0.0
ENV PAL_SERVER_PORT=8090

EXPOSE 8090

# Run the server
CMD ["python", "-m", "pal"]
