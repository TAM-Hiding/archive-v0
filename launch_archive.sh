#!/usr/bin/env bash

set -euo pipefail

# Always operate relative to this script, regardless of where it was launched.
ARCHIVE_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ARCHIVE_URL="http://127.0.0.1:5000"

cd "$ARCHIVE_DIR"

# If Archive is already responding, just open it.
if curl --silent --fail "$ARCHIVE_URL" >/dev/null 2>&1; then
    xdg-open "$ARCHIVE_URL" >/dev/null 2>&1 &
    exit 0
fi

# Start Archive in the background and retain a log for troubleshooting.
nohup python3 app.py > archive.log 2>&1 &
ARCHIVE_PID=$!

# Wait up to about 10 seconds for Flask to become available.
for _ in {1..40}; do
    if curl --silent --fail "$ARCHIVE_URL" >/dev/null 2>&1; then
        xdg-open "$ARCHIVE_URL" >/dev/null 2>&1 &
        exit 0
    fi

    # Fail early if Python exited during startup.
    if ! kill -0 "$ARCHIVE_PID" 2>/dev/null; then
        echo "Archive failed to start. Check:"
        echo "  $ARCHIVE_DIR/archive.log"
        exit 1
    fi

    sleep 0.25
done

echo "Archive did not respond within 10 seconds."
echo "Check:"
echo "  $ARCHIVE_DIR/archive.log"
exit 1
