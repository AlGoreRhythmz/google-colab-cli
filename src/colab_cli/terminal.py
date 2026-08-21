"""
🤖 TEMP_ADDRESS_ROUTE: Real terminal server with WebSocket
Connects to actual shell session for direct terminal access
"""

import os
import subprocess
import json
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import logging

logger = logging.getLogger(__name__)

# 🤖 TERMINAL_UI: Web-based terminal interface
TERMINAL_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Terminal - Claude Code</title>
    <script src="https://cdn.jsdelivr.net/npm/xterm@5.3.0/lib/xterm.js"></script>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/xterm@5.3.0/css/xterm.css" />
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        html, body {
            width: 100%;
            height: 100%;
            background: #1e1e1e;
            font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
        }
        #terminal-container {
            width: 100%;
            height: 100%;
            overflow: hidden;
        }
        .xterm {
            height: 100%;
        }
    </style>
</head>
<body>
    <div id="terminal-container"></div>
    <script>
        // 🤖 WEBSOCKET_HANDLER: Terminal multiplexing via WebSocket
        const terminal = new Terminal({
            cursorBlink: true,
            theme: {
                background: '#1e1e1e',
                foreground: '#d4d4d4',
            },
            fontSize: 14,
            fontFamily: "'Monaco', 'Menlo', 'Ubuntu Mono', monospace",
        });

        terminal.open(document.getElementById('terminal-container'));
        terminal.write('\\r\\n🤖 Terminal Connected\\r\\n');
        terminal.write('Type your commands below:\\r\\n\\r\\n');

        let ws = null;

        function connectTerminal() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            ws = new WebSocket(`${protocol}//${window.location.host}/ws/terminal`);

            ws.onopen = () => {
                terminal.write('✓ Connected to session\\r\\n');
            };

            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                if (data.type === 'output') {
                    terminal.write(data.output);
                } else if (data.type === 'error') {
                    terminal.write(`\\r\\n[ERROR] ${data.message}\\r\\n`);
                }
            };

            ws.onerror = () => {
                terminal.write('\\r\\n[Connection Error]\\r\\n');
            };

            ws.onclose = () => {
                terminal.write('\\r\\n[Disconnected]\\r\\n');
                setTimeout(connectTerminal, 2000);
            };
        }

        // Send input to terminal
        terminal.onData((input) => {
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({
                    type: 'input',
                    data: input
                }));
            }
        });

        connectTerminal();
    </script>
</body>
</html>
"""

app = FastAPI(title="Terminal Server")

# 🤖 TEMP_ADDRESS_ROUTE: Serve terminal at /terminal
@app.get("/terminal")
async def get_terminal():
    """Real terminal interface"""
    return HTMLResponse(content=TERMINAL_HTML)

@app.get("/")
async def root():
    """Redirect to terminal"""
    return HTMLResponse(
        content='<html><head><meta http-equiv="refresh" content="0;url=/terminal" /></head></html>'
    )

# 🤖 WEBSOCKET_HANDLER: Terminal shell process
@app.websocket("/ws/terminal")
async def websocket_terminal(websocket: WebSocket):
    """
    Real interactive shell via WebSocket
    Spawns an actual shell process and multiplexes I/O
    """
    await websocket.accept()

    # Spawn a real shell process
    process = subprocess.Popen(
        ['/bin/bash', '--login'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        bufsize=0,
        universal_newlines=True
    )

    async def read_output():
        """Read shell output and send to client"""
        loop = asyncio.get_event_loop()
        while True:
            try:
                output = await loop.run_in_executor(None, process.stdout.read, 1)
                if not output:
                    break
                await websocket.send_json({
                    'type': 'output',
                    'output': output
                })
            except Exception as e:
                logger.error(f"Read error: {e}")
                break

    try:
        # Start reading output in background
        read_task = asyncio.create_task(read_output())

        # Handle incoming input
        while True:
            try:
                data = await websocket.receive_text()
                msg = json.loads(data)
                if msg.get('type') == 'input':
                    process.stdin.write(msg.get('data', ''))
                    process.stdin.flush()
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                break

        read_task.cancel()
    finally:
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
        logger.info("Terminal session closed")


def run_terminal(host: str = "0.0.0.0", port: int = 8000):
    """
    Start the terminal server

    Usage:
        from colab_cli.terminal import run_terminal
        run_terminal()
    """
    import uvicorn
    logger.info(f"Starting Terminal Server at http://{host}:{port}/terminal")
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    run_terminal()
