from fastapi import APIRouter
from starlette.requests import Request

from core.template import UserTemplates
from .. import plugin_config
from ..plugin_config import module_name

router = APIRouter()

templates = UserTemplates()


from typing import List
from fastapi import WebSocket
from fastapi.responses import HTMLResponse

html = """
<!DOCTYPE html>
<html>
    <head>
        <title>WebSocket Test</title>
    </head>
    <body>
        <h1>WebSocket Chat</h1>
        <textarea id="chatLog" cols="100" rows="20"></textarea><br>
        <input type="text" id="inputText" autocomplete="off"/><button onclick="sendMessage()">Send</button>
        <p id="status">Disconnected</p>
        <script>
            var ws = new WebSocket("ws://114.207.112.249:8000/ws/message");
            ws.onopen = function() {
                document.getElementById("status").textContent = "Connected";
                console.log("Connected to the WebSocket server");
            };
            ws.onclose = function() {
                document.getElementById("status").textContent = "Disconnected";
                console.log("Disconnected from the WebSocket server");
            };
            ws.onerror = function(error) {
                console.log("WebSocket Error: " + error);
            };

            ws.onmessage = function(event) {
                var messages = document.getElementById('chatLog');
                console.log("Message from server ", messages.value);
                messages.value += event.data + '\\n';
            };
            function sendMessage() {
                var input = document.getElementById("inputText");
                console.log("Sending message: " + input.value);
                ws.send(input.value);
                input.value = '';
            }
        </script>
    </body>
</html>
"""

@router.get("/")
async def get():
    return HTMLResponse(html)

# WebSocket 연결을 처리할 리스트
connections: List[WebSocket] = []

import logging
from fastapi import WebSocketDisconnect

# 로깅 설정: 기본 수준은 INFO이며, 로그는 'app.log' 파일에 기록됩니다.
logging.basicConfig(level=logging.INFO, filename='test.log', filemode='a',
                    format='%(asctime)s - %(levelname)s - %(message)s')

# 로거를 사용하여 로그 메시지 기록
logging.info("This is an info message")

@router.websocket("/message")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connections.append(websocket)
    logging.info(f"WebSocket connection established: {websocket.client}")
    try:
        while True:
            data = await websocket.receive_text()
            logging.info(f"Received message: {data} from {websocket.client}")
            await broadcast_message(data, websocket)
    except WebSocketDisconnect:
        connections.remove(websocket)
        logging.info(f"WebSocket connection closed: {websocket.client}")
    except Exception as e:
        logging.error(f"Error in websocket connection: {e}")
        connections.remove(websocket)

async def broadcast_message(data: str, sender: WebSocket):
    for connection in connections:
        if connection != sender:
            try:
                await connection.send_text(f"Message: {data}")
                logging.info(f"Message sent to {connection.client}")
            except Exception as e:
                logging.error(f"Error sending message: {e}")
