FROM python:3.11-slim
WORKDIR /app
RUN pip install mcp uvicorn
COPY server.py config.py instructions.py tools.py ./
COPY files files/
COPY prompts prompts/
EXPOSE 8090
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8090"]
