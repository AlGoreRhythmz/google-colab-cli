"""
🤖 TEMP_ADDRESS_ROUTE: Public proxy to local chat server
Exposes localhost:8000 to external access via HTTP proxy
"""

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
import urllib.request
import json

app = FastAPI(title="Chat Proxy")

# Target local server
LOCAL_URL = "http://127.0.0.1:8000"

@app.get("/")
async def root():
    return HTMLResponse("""
    <html>
        <head>
            <meta http-equiv="refresh" content="0;url=/proxy/chat" />
        </head>
    </html>
    """)

@app.get("/proxy/chat")
async def proxy_chat():
    """🤖 TEMP_ADDRESS_ROUTE: Proxy /chat endpoint"""
    try:
        with urllib.request.urlopen(f"{LOCAL_URL}/chat", timeout=10) as response:
            return HTMLResponse(response.read().decode())
    except Exception as e:
        return HTMLResponse(f"<h1>Error: {e}</h1>", status_code=500)

@app.get("/proxy/history")
async def proxy_history():
    """Proxy /history endpoint"""
    try:
        with urllib.request.urlopen(f"{LOCAL_URL}/history", timeout=10) as response:
            return json.loads(response.read().decode())
    except Exception as e:
        return {"error": str(e)}

@app.get("/proxy/history.txt")
async def proxy_history_txt():
    """Proxy /history.txt endpoint"""
    try:
        with urllib.request.urlopen(f"{LOCAL_URL}/history.txt", timeout=10) as response:
            return HTMLResponse(response.read().decode())
    except Exception as e:
        return HTMLResponse(f"<h1>Error: {e}</h1>", status_code=500)

@app.websocket("/proxy/ws/chat")
async def proxy_websocket(websocket):
    """🤖 WEBSOCKET_HANDLER: Proxy WebSocket"""
    # Note: Simple proxy - may need enhancement for full duplex
    await websocket.accept()
    await websocket.send_text("Connected to proxy")

if __name__ == "__main__":
    import uvicorn
    print("🔗 Proxy running on 0.0.0.0:9000")
    print("📍 Access at: http://0.0.0.0:9000/proxy/chat")
    uvicorn.run(app, host="0.0.0.0", port=9000)
