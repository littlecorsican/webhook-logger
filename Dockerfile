# Use a small Python base image
FROM python:3.12-slim

# Set work directory inside the container
WORKDIR /app

# Install system dependencies (if needed for some libs) and clean up
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the app code
COPY . .

# Expose the port FastAPI will run on
EXPOSE 9000

# Environment variables for Redis configuration
ENV REDIS_HOST=redis \
    REDIS_PORT=6379 \
    REDIS_DB=0 \
    REDIS_USERNAME= \
    REDIS_PASSWORD=

# Run the FastAPI app with uvicorn
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "9000"]
