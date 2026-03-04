# claudestrap

Minimum self-bootstrapping Claude app. Three files, one loop. Tell the agent to modify itself. It will. 


## What it is

A Claude agent that can modify and restart itself.

start.sh runs run_minimum.py, agent edits its own code, agent sends kill -USR1 to itself, exits with code 42, start.sh restarts it, new code is live


## Files

| File | Purpose |
|------|---------|
| `app_minimum.py` | HTTP server serving an inline chat UI (port 8001) |
| `run_minimum.py` | WebSocket server wrapping the Claude Agent SDK (port 8766) |
| `start.sh` | Restart loop — restarts the agent on exit code 42 |

## Usage

```bash
pip install claude-agent-sdk websockets
./start.sh
# open http://localhost:8001, talk.
