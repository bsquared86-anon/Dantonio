from typing import Dict, Any, List
from datetime import datetime
import logging
from fastapi import WebSocket
from app.database.repository.position_repository import PositionRepository
from app.database.repository.transaction_repository import TransactionRepository
from app.core.monitoring import get_system_metrics

logger = logging.getLogger(__name__)

class FrontendService:
    def __init__(self, position_repo: PositionRepository, transaction_repo: TransactionRepository):
        self.position_repo = position_repo
        self.transaction_repo = transaction_repo
        self._active_connections: List[WebSocket] = []

    async def get_dashboard_data(self) -> Dict[str, Any]:
        """Get all data needed for the dashboard"""
        try:
            return {
                "positions": await self.get_active_positions(),
                "transactions": await self.get_recent_transactions(),
                "metrics": await self.get_system_metrics(),
                "performance": await self.get_performance_metrics()
            }
        except Exception as e:
            logger.error(f"Error getting dashboard data: {str(e)}")
            raise

    async def get_active_positions(self) -> List[Dict[str, Any]]:
        positions = await self.position_repo.get_active_positions()
        return [position.to_dict() for position in positions]

    async def get_recent_transactions(self) -> List[Dict[str, Any]]:
        transactions = await self.transaction_repo.get_recent_transactions(limit=50)
        return [tx.to_dict() for tx in transactions]

    async def get_system_metrics(self) -> Dict[str, Any]:
        return {
            "system": get_system_metrics(),
            "timestamp": datetime.utcnow().isoformat()
        }

    async def get_performance_metrics(self) -> Dict[str, Any]:
        return {
            "total_profit": await self.position_repo.get_total_profit(),
            "success_rate": await self.position_repo.get_success_rate(),
            "average_return": await self.position_repo.get_average_return()
        }

    async def register_websocket(self, websocket: WebSocket):
        await websocket.accept()
        self._active_connections.append(websocket)

    async def unregister_websocket(self, websocket: WebSocket):
        self._active_connections.remove(websocket)

    async def broadcast_update(self, message: Dict[str, Any]):
        for connection in self._active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to websocket: {str(e)}")
                await self.unregister_websocket(connection)

