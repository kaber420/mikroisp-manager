
from typing import List
from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast_event(self, event_type: str, data: dict = None):
        """
        Envía una señal JSON genérica a todos los clientes conectados.
        """
        payload = {"type": event_type}
        if data:
            payload.update(data)

        # Iteramos sobre una copia [:] para evitar errores si la lista cambia durante el envío
        for connection in self.active_connections[:]:
            try:
                await connection.send_json(payload)
            except Exception:
                self.disconnect(connection)

manager = ConnectionManager()
