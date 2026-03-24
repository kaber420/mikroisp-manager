from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, List

router = APIRouter()

# Gestor de conexiones para el pool de soporte
class SupportPoolManager:
    def __init__(self):
        # tech_id: WebSocket
        self.active_techs: Dict[str, WebSocket] = {}
        # ticket_id: WebSocket
        self.waiting_clients: Dict[str, WebSocket] = {}

    async def connect_tech(self, websocket: WebSocket, tech_id: str):
        await websocket.accept()
        self.active_techs[tech_id] = websocket

    def disconnect_tech(self, tech_id: str):
        if tech_id in self.active_techs:
            del self.active_techs[tech_id]

    async def connect_client(self, websocket: WebSocket, ticket_id: str):
        await websocket.accept()
        self.waiting_clients[ticket_id] = websocket
        await self.broadcast_pool_update()

    def disconnect_client(self, ticket_id: str):
        if ticket_id in self.waiting_clients:
            del self.waiting_clients[ticket_id]
            # Emitir actualización a técnicos de forma asíncrona
            # await self.broadcast_pool_update() no se puede llamar directamente aquí sin un event loop

    async def broadcast_pool_update(self):
        """Envía la cantidad de clientes esperando a los técnicos"""
        waiting_count = len(self.waiting_clients)
        for connection in self.active_techs.values():
            await connection.send_json({"waiting_count": waiting_count, "action": "update_pool"})
            
    async def notify_client_accepted(self, ticket_id: str):
        """Notifica al cliente que su ticket fue aceptado para que cargue LiveKit"""
        if ticket_id in self.waiting_clients:
            client_socket = self.waiting_clients[ticket_id]
            await client_socket.send_json({"action": "ticket_accepted"})
            # El cliente puede desconectarse del WS una vez entra a LiveKit

pool_manager = SupportPoolManager()

@router.websocket("/ws/support/pool/tech/{tech_id}")
async def tech_pool_endpoint(websocket: WebSocket, tech_id: str):
    await pool_manager.connect_tech(websocket, tech_id)
    try:
        while True:
            data = await websocket.receive_text()
            # Posible lógica (ping/pong)
    except WebSocketDisconnect:
        pool_manager.disconnect_tech(tech_id)

@router.websocket("/ws/support/pool/client/{ticket_id}")
async def client_pool_endpoint(websocket: WebSocket, ticket_id: str):
    await pool_manager.connect_client(websocket, ticket_id)
    try:
        while True:
            data = await websocket.receive_text()
            # Esperando notificaciones
    except WebSocketDisconnect:
        pool_manager.disconnect_client(ticket_id)
        # Necesitamos una manera asíncrona de avisar que un cliente se desconectó
