#!/bin/bash
# Start iceman-server (run from project root OR from iceman_server/)
#
# First-time setup:
#   conda env create -f environment.yml
#   conda activate iceman
#
# Then start:
#   ./start.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Load .env if present
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi

echo "Starting iceman-server on http://0.0.0.0:8080"
echo "API docs: http://localhost:8080/docs"
echo ""

uvicorn app:app --host 0.0.0.0 --port 8080 --reload
