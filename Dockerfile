FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY src/ ./src/
COPY config.yaml run.py ./

# Create data directory
RUN mkdir -p /app/data

ENV PYTHONUNBUFFERED=1

CMD ["python", "run.py"]
