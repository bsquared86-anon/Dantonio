import logging
import asyncio
import json
from typing import Dict, List, Optional, Callable
import websockets
from websockets.exceptions import ConnectionClosed
from app.core.config import config

logger = logging.getLogger(__name__)

class WebSocketManager:
    def __init__(self):
        self.connections: Dict[str, Dict] = {}
        self.subscribers: Dict[str, List[Callable]] = {}
        self.is_running = False
        self.reconnect_interval = config.get('websocket.reconnect_interval', 5)
        self.max_reconnect_attempts = config.get('websocket.max_reconnect_attempts', 5)

    async def connect(self, url: str, channel: str) -> bool:
        try:
            if channel in self.connections:
                logger.warning(f"Channel {channel} already connected")
                return False

            connection = {
                'url': url,
                'channel': channel,
                'websocket': None,
                'reconnect_attempts': 0,
                'is_connected': False
            }

            self.connections[channel] = connection
            asyncio.create_task(self._maintain_connection(channel))
            logger.info(f"Initialized connection for channel {channel}")
            return True

        except Exception as e:
            logger.error(f"Error connecting to websocket: {str(e)}")
            return False

    async def _maintain_connection(self, channel: str):
        while channel in self.connections:
            connection = self.connections[channel]
            
            try:
                if not connection['is_connected']:
                    async with websockets.connect(connection['url']) as websocket:
                        connection['websocket'] = websocket
                        connection['is_connected'] = True
                        connection['reconnect_attempts'] = 0
                        
                        logger.info(f"Connected to channel {channel}")
                        await self._handle_messages(channel)

            except ConnectionClosed:
                logger.warning(f"Connection closed for channel {channel}")
                await self._handle_disconnection(channel)
                
            except Exception as e:
                logger.error(f"Error in websocket connection: {str(e)}")
                await self._handle_disconnection(channel)

            await asyncio.sleep(self.reconnect_interval)

    async def _handle_messages(self, channel: str):
        connection = self.connections[channel]
        websocket = connection['websocket']

        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self._process_message(channel, data)
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON received on channel {channel}")
                except Exception as e:
                    logger.error(f"Error processing message: {str(e)}")

        except Exception as e:
            logger.error(f"Error handling messages: {str(e)}")

    async def _process_message(self, channel: str, data: Dict):
        if channel in self.subscribers:
            for callback in self.subscribers[channel]:
                try:
                    await callback(data)
                except Exception as e:
                    logger.error(f"Error in subscriber callback: {str(e)}")

    async def _handle_disconnection(self, channel: str):
        connection = self.connections[channel]
        connection['is_connected'] = False
        connection['websocket'] = None
        connection['reconnect_attempts'] += 1

        if connection['reconnect_attempts'] >= self.max_reconnect_attempts:
            logger.error(f"Max reconnection attempts reached for channel {channel}")
            await self.disconnect(channel)

    async def disconnect(self, channel: str) -> bool:
        try:
            if channel not in self.connections:
                return False

            connection = self.connections[channel]
            if connection['websocket']:
                await connection['websocket'].close()

            del self.connections[channel]
            if channel in self.subscribers:
                del self.subscribers[channel]

            logger.info(f"Disconnected from channel {channel}")
            return True

        except Exception as e:
            logger.error(f"Error disconnecting from websocket: {str(e)}")
            return False

    async def subscribe(self, channel: str, callback: Callable) -> bool:
        try:
            if channel not in self.subscribers:
                self.subscribers[channel] = []
            
            if callback not in self.subscribers[channel]:
                self.subscribers[channel].append(callback)
                logger.info(f"Subscribed to channel {channel}")
                return True

            return False

        except Exception as e:
            logger.error(f"Error subscribing to channel: {str(e)}")
            return False

    async def unsubscribe(self, channel: str, callback: Callable) -> bool:
        try:
            if channel in self.subscribers and callback in self.subscribers[channel]:
                self.subscribers[channel].remove(callback)
                logger.info(f"Unsubscribed from channel {channel}")
                return True

            return False

        except Exception as e:
            logger.error(f"Error unsubscribing from channel: {str(e)}")
            return False

    async def send_message(self, channel: str, message: Dict) -> bool:
        try:
            if channel not in self.connections:
                logger.warning(f"Channel {channel} not connected")
                return False

            connection = self.connections[channel]
            if not connection['is_connected']:
                logger.warning(f"Channel {channel} not connected")
                return False

            await connection['websocket'].send(json.dumps(message))
            return True

        except Exception as e:
            logger.error(f"Error sending message: {str(e)}")
            return False

    def get_connection_status(self, channel: str) -> Optional[Dict]:
        try:
            if channel in self.connections:
                connection = self.connections[channel]
                return {
                    'is_connected': connection['is_connected'],
                    'reconnect_attempts': connection['reconnect_attempts']
                }
            return None

        except Exception as e:
            logger.error(f"Error getting connection status: {str(e)}")
            return None

