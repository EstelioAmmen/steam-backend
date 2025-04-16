#!/bin/bash

WATCHED_DIR="/root/Site"

inotifywait -mrq -e modify,create,delete,move "$WATCHED_DIR" --exclude '\.git|__pycache__|\.pyc|\.log' |
while read path action file; do
    echo "[INFO] Изменение обнаружено: $action $file"
    cd "$WATCHED_DIR"
    
    git add .
    git commit -m "Auto update on file change: $file"
    git push
done
