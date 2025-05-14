FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Expose port
EXPOSE 5000

# Run with gunicorn for production
CMD ["gunicorn", "-b", "0.0.0.0:5000", "app:app", "--workers=4"]