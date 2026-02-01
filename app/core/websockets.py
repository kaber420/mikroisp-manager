import asyncio
import json
import logging

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self._listener_started: bool = False

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

    async def start_redict_listener(self):
        """
        Inicia un listener para Redict Pub/Sub y reenvía eventos a websockets.
        Se ejecuta como background task durante el lifespan de la app.
        """
        if self._listener_started:
            return  # Ya está corriendo
        
        self._listener_started = True
        
        try:
            from app.utils.cache.redict_store import redict_manager
            
            if not redict_manager.is_connected:
                logger.info("Redict no conectado, listener Pub/Sub no iniciado")
                self._listener_started = False
                return
            
            pubsub = redict_manager.get_pubsub()
            if not pubsub:
                self._listener_started = False
                return
            
            await pubsub.subscribe("chat:updates")
            logger.info("✅ Escuchando canal 'chat:updates' de Redict")
            
            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        # Decodificar bytes a string si es necesario
                        raw_data = message["data"]
                        if isinstance(raw_data, bytes):
                            raw_data = raw_data.decode("utf-8")
                        
                        data = json.loads(raw_data)
                        event_type = data.pop("type", "update")
                        await self.broadcast_event(event_type, data)
                    except json.JSONDecodeError as e:
                        logger.warning(f"Invalid JSON from Redict: {e}")
                    except Exception as e:
                        logger.warning(f"Error processing Redict message: {e}")
                        
        except ImportError:
            logger.info("Redict listener no iniciado (redis no instalado)")
        except Exception as e:
            logger.error(f"Error en Redict listener: {e}")
        finally:
            self._listener_started = False


manager = ConnectionManager()

