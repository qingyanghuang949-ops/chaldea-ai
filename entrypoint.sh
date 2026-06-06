#!/bin/bash
set -e

# Download database if DB_URL is set and fgo_wiki.db doesn't exist
if [ -n "$DB_URL" ] && [ ! -f fgo_wiki.db ]; then
    echo "Downloading database from $DB_URL ..."
    curl -L -o fgo_wiki.db "$DB_URL"
    echo "Database downloaded ($(du -h fgo_wiki.db | cut -f1))"
fi

# Start gunicorn
exec gunicorn --bind 0.0.0.0:5000 --workers 2 --timeout 120 chat_system.app:app
