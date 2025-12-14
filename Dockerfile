FROM python:3.11-slim
WORKDIR /app
RUN pip install fastapi uvicorn
COPY mcp_server.py .
COPY files files/
EXPOSE 8090
CMD ["uvicorn", "mcp_server:app", "--host", "0.0.0.0", "--port", "8090"]
