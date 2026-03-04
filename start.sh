#!/bin/bash
# Minimal wrapper: serves chat UI + runs agent with restart-on-42
cd "$(dirname "$0")"

python3 app_minimal.py &
APP_PID=$!
echo "Chat UI on http://0.0.0.0:8001 (pid $APP_PID)"

cleanup() {
    kill $APP_PID 2>/dev/null
    exit 0
}
trap cleanup EXIT INT TERM

while true; do
    python3 run_minimal.py
    code=$?
    if [ $code -ne 42 ]; then
        echo "run_minimal.py exited with code $code, stopping."
        break
    fi
    echo "Restarting run_minimal.py..."
    sleep 1
done
