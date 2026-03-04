"""Minimal Claude Code agent with websocket interface that can restart itself via PID + SIGUSR1."""
import asyncio
import json
import os
import signal
import sys

import websockets

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
)

RESTART_EXIT_CODE = 42
PID_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".minimal.pid")
CWD = os.path.dirname(os.path.abspath(__file__))
WS_PORT = 8766

# Connected browser clients
clients: set = set()
agent: ClaudeSDKClient | None = None


async def broadcast(msg: dict):
    """Send a JSON message to all connected clients."""
    raw = json.dumps(msg)
    for ws in list(clients):
        try:
            await ws.send(raw)
        except Exception:
            clients.discard(ws)


async def ensure_agent():
    """Create and connect the agent if not already running."""
    global agent
    if agent is not None:
        return

    agent = ClaudeSDKClient(
        options=ClaudeAgentOptions(
            model="claude-opus-4-6",
            permission_mode="bypassPermissions",
            cwd=CWD,
            system_prompt=(
                "You are a minimal agent. You can read/write files and run commands. "
                f"To restart yourself, run: kill -USR1 $(cat {PID_FILE})"
            ),
        )
    )
    await agent.connect()
    print("Agent connected.")

    # Start background receiver
    asyncio.create_task(message_receiver())


async def message_receiver():
    """Read messages from the agent and broadcast to clients."""
    if not agent:
        return

    try:
        async for message in agent.receive_messages():
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        await broadcast({"type": "text", "content": block.text})
                    elif isinstance(block, ToolUseBlock):
                        await broadcast({"type": "tool_use", "tool": block.name, "input": str(block.input)[:200]})
            elif isinstance(message, ResultMessage):
                await broadcast({"type": "done"})
    except Exception as e:
        print(f"[receiver] Error: {e}")
        await broadcast({"type": "text", "content": f"Agent error: {e}"})
        await broadcast({"type": "done"})


async def handle_connection(websocket):
    """Handle a websocket connection."""
    clients.add(websocket)
    print(f"[ws] Client connected. Total: {len(clients)}")

    try:
        async for raw in websocket:
            msg = json.loads(raw)

            if msg.get("type") == "user":
                content = msg.get("content", "").strip()
                if not content:
                    continue

                await broadcast({"type": "user_echo", "content": content})
                await ensure_agent()
                asyncio.create_task(agent.query(content))

            elif msg.get("type") == "stop":
                if agent:
                    await agent.interrupt()
                await broadcast({"type": "done"})

    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        clients.discard(websocket)
        print(f"[ws] Client disconnected. Total: {len(clients)}")


async def main():
    global agent

    # Write PID so the agent can signal us
    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))
    print(f"PID {os.getpid()} written to {PID_FILE}")

    stop = asyncio.Event()
    restart = asyncio.Event()
    loop = asyncio.get_running_loop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)
    loop.add_signal_handler(signal.SIGUSR1, restart.set)

    async with websockets.serve(handle_connection, "0.0.0.0", WS_PORT):
        print(f"WebSocket server on ws://0.0.0.0:{WS_PORT}")
        print("Send JSON: {\"type\": \"user\", \"content\": \"hello\"}")

        while not stop.is_set() and not restart.is_set():
            await asyncio.sleep(1)

    # Teardown
    if agent:
        await agent.disconnect()
        agent = None

    # Clean up PID file
    try:
        os.remove(PID_FILE)
    except OSError:
        pass

    if restart.is_set():
        print("Restart requested, exiting with code 42...")
        sys.exit(RESTART_EXIT_CODE)


if __name__ == "__main__":
    asyncio.run(main())
