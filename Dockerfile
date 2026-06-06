FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install curl for downloading db
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Copy application
COPY chat_system/ chat_system/
COPY 基本资料/图标/ 基本资料/图标/
COPY 基本资料/mooncell头像/ 基本资料/mooncell头像/

# Download database from release URL (set DB_URL env var on Render)
ARG DB_URL
RUN if [ -n "$DB_URL" ]; then curl -L -o fgo_wiki.db "$DB_URL"; fi

# Expose port
EXPOSE 5000

# Start with gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "120", "chat_system.app:app"]
