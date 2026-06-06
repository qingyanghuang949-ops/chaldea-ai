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

# Copy entrypoint
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

# Expose port
EXPOSE 5000

# Start with entrypoint (downloads db if needed, then starts gunicorn)
CMD ["./entrypoint.sh"]
