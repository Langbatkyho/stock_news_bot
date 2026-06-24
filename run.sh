#!/bin/bash
cd "$(dirname "$0")" || exit
export PYTHONUTF8=1
if [ -d ".venv" ]; then
    source .venv/bin/activate
elif [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d "../.venv" ]; then
    source ../.venv/bin/activate
elif [ -d "$HOME/.venv" ]; then
    source "$HOME/.venv/bin/activate"
fi
mkdir -p logs
nohup python3 main.py > logs/nohup.out 2>&1 &
echo "Bot started in background. Logs can be found in logs/nohup.out."
