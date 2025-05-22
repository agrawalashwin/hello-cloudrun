# Use the official Python image.
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# 1. Install dependencies first (cached if requirements.txt unchanged)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 2. Copy the rest of your application code
COPY . .

# 3. Expose the port Cloud Run expects
ENV PORT 8080
EXPOSE 8080

# 4. Launch your app with Gunicorn instead of the dev server
#    - 2 worker processes is a reasonable default
CMD ["gunicorn", "main:app", "--bind", "0.0.0.0:8080", "--workers", "2"]
