#!/bin/zsh
cd "$(dirname "$0")" || exit 1

if [[ ! -x ".venv/bin/python" ]]; then
  echo "The project virtual environment was not found. Run the setup steps in README.md first."
  read -k 1 "?Press any key to close..."
  exit 1
fi

".venv/bin/python" -m script_to_shorts.webapp &
server_pid=$!
trap 'kill "$server_pid" 2>/dev/null' EXIT INT TERM
sleep 1
open "http://127.0.0.1:8765"
wait "$server_pid"
