"""
Phone Chat Web Interface for Colab CLI.

This module provides a simple, working phone-style chat interface.
Serves over HTTP/WebSockets for temporary debugging and testing.

🤖 BOT NAVIGATION MARKERS:
- PHONE_CHAT_INTERFACE: Main chat UI component
- TEMP_ADDRESS_ROUTE: Temporary address serving the interface
- WEBSOCKET_HANDLER: Real-time message handling
"""

import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import logging

logger = logging.getLogger(__name__)

# 🤖 PHONE_CHAT_INTERFACE: The main chat HTML page
PHONE_CHAT_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Colab Chat</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 10px;
        }

        .phone-frame {
            width: 100%;
            max-width: 400px;
            height: 600px;
            background: white;
            border-radius: 40px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            overflow: hidden;
            display: flex;
            flex-direction: column;
            border: 8px solid #1a1a1a;
            position: relative;
        }

        .notch {
            position: absolute;
            top: 0;
            left: 50%;
            transform: translateX(-50%);
            width: 150px;
            height: 25px;
            background: #1a1a1a;
            border-radius: 0 0 20px 20px;
            z-index: 10;
        }

        .chat-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 12px 16px;
            text-align: center;
            margin-top: 15px;
            font-size: 14px;
            font-weight: 600;
        }

        .chat-container {
            flex: 1;
            overflow-y: auto;
            padding: 16px;
            display: flex;
            flex-direction: column;
            gap: 12px;
        }

        .message {
            display: flex;
            animation: slideIn 0.3s ease-out;
        }

        .message.user {
            justify-content: flex-end;
        }

        .message.assistant {
            justify-content: flex-start;
        }

        .message-content {
            max-width: 70%;
            padding: 10px 12px;
            border-radius: 18px;
            word-wrap: break-word;
            font-size: 14px;
            line-height: 1.4;
        }

        .message.user .message-content {
            background: #667eea;
            color: white;
            border-bottom-right-radius: 4px;
        }

        .message.assistant .message-content {
            background: #f0f0f0;
            color: #333;
            border-bottom-left-radius: 4px;
        }

        .message.system .message-content {
            background: #f9f9f9;
            color: #666;
            font-size: 12px;
            font-style: italic;
            border-radius: 12px;
            margin: 8px auto;
        }

        @keyframes slideIn {
            from {
                opacity: 0;
                transform: translateY(10px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        .input-area {
            padding: 12px;
            border-top: 1px solid #e0e0e0;
            display: flex;
            gap: 8px;
            background: white;
        }

        .input-area input {
            flex: 1;
            border: 1px solid #e0e0e0;
            border-radius: 20px;
            padding: 10px 16px;
            font-size: 14px;
            outline: none;
            transition: border-color 0.2s;
        }

        .input-area input:focus {
            border-color: #667eea;
        }

        .input-area button {
            width: 36px;
            height: 36px;
            border: none;
            border-radius: 50%;
            background: #667eea;
            color: white;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 18px;
            transition: background 0.2s;
        }

        .input-area button:hover {
            background: #764ba2;
        }

        .input-area button:active {
            transform: scale(0.95);
        }

        .chat-container::-webkit-scrollbar {
            width: 6px;
        }

        .chat-container::-webkit-scrollbar-track {
            background: transparent;
        }

        .chat-container::-webkit-scrollbar-thumb {
            background: #ccc;
            border-radius: 3px;
        }

        .status {
            padding: 8px 12px;
            font-size: 12px;
            color: #999;
            text-align: center;
            background: #f9f9f9;
        }
    </style>
</head>
<body>
    <div class="phone-frame">
        <div class="notch"></div>
        <div class="chat-header">Colab Chat 💬</div>
        <div class="chat-container" id="chatContainer"></div>
        <div class="status" id="status">Connected</div>
        <div class="input-area">
            <input
                type="text"
                id="messageInput"
                placeholder="Type a message..."
                autocomplete="off"
            >
            <button id="sendBtn">➤</button>
        </div>
    </div>

    <script>
        // 🤖 WEBSOCKET_HANDLER: Manages real-time communication
        const chatContainer = document.getElementById('chatContainer');
        const messageInput = document.getElementById('messageInput');
        const sendBtn = document.getElementById('sendBtn');
        const status = document.getElementById('status');

        let ws = null;

        function connectWebSocket() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            ws = new WebSocket(`${protocol}//${window.location.host}/ws/chat`);

            ws.onopen = () => {
                status.textContent = 'Connected ✓';
                addSystemMessage('Connected to Colab');
            };

            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                if (data.type === 'message') {
                    addMessage(data.content, data.sender);
                } else if (data.type === 'error') {
                    addSystemMessage(`Error: ${data.content}`, 'error');
                }
            };

            ws.onerror = () => {
                status.textContent = 'Connection error';
                addSystemMessage('Connection error', 'error');
            };

            ws.onclose = () => {
                status.textContent = 'Disconnected';
                setTimeout(connectWebSocket, 3000);
            };
        }

        function addMessage(content, sender = 'assistant') {
            const msgDiv = document.createElement('div');
            msgDiv.className = `message ${sender}`;

            const contentDiv = document.createElement('div');
            contentDiv.className = 'message-content';
            contentDiv.textContent = content;

            msgDiv.appendChild(contentDiv);
            chatContainer.appendChild(msgDiv);
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }

        function addSystemMessage(content, type = 'system') {
            const msgDiv = document.createElement('div');
            msgDiv.className = `message ${type}`;

            const contentDiv = document.createElement('div');
            contentDiv.className = 'message-content';
            contentDiv.textContent = content;

            msgDiv.appendChild(contentDiv);
            chatContainer.appendChild(msgDiv);
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }

        function sendMessage() {
            const text = messageInput.value.trim();
            if (!text) return;

            addMessage(text, 'user');
            messageInput.value = '';

            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({
                    type: 'message',
                    content: text
                }));
            } else {
                addSystemMessage('Not connected', 'error');
            }
        }

        sendBtn.addEventListener('click', sendMessage);
        messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') sendMessage();
        });

        // Connect on page load
        connectWebSocket();
    </script>
</body>
</html>
"""

# 🤖 TEMP_ADDRESS_ROUTE: Serves the chat interface at /chat
app = FastAPI(title="Colab Chat Server")


@app.get("/chat")
async def get_chat_page() -> HTMLResponse:
    """
    🤖 TEMP_ADDRESS_ROUTE: Main phone chat page.
    Serves the phone-style chat interface.
    Access at: http://localhost:8000/chat
    """
    return HTMLResponse(content=PHONE_CHAT_HTML)


@app.get("/")
async def root():
    """Redirect to chat page"""
    return HTMLResponse(
        content="""
        <html>
            <head>
                <meta http-equiv="refresh" content="0;url=/chat" />
            </head>
            <body>
                <a href="/chat">Go to chat</a>
            </body>
        </html>
        """
    )


@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    """
    🤖 WEBSOCKET_HANDLER: Real-time message handling.
    Accepts WebSocket connections and echoes messages back.
    """
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            if message.get("type") == "message":
                content = message.get("content", "")
                logger.info(f"Received message: {content}")

                # Echo the message back as assistant response
                response = {
                    "type": "message",
                    "content": f"You said: {content}",
                    "sender": "assistant"
                }
                await websocket.send_json(response)

    except WebSocketDisconnect:
        logger.info("Client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "content": str(e)
            })
        except:
            pass


def run_server(host: str = "127.0.0.1", port: int = 8000):
    """
    🤖 BOT NAVIGATION MARKERS: Start the phone chat server

    Usage:
        from colab_cli.web import run_server
        run_server()

    Then visit: http://localhost:8000/chat
    """
    import uvicorn
    logger.info(f"Starting Colab Chat Server at http://{host}:{port}/chat")
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    run_server()
