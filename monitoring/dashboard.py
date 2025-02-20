from typing import Dict, Any, List
import asyncio
import logging
from datetime import datetime
from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

class MonitoringDashboard:
    def __init__(self, config: Dict[str, Any]):
        self.logger = logging.getLogger(__name__)
        self.config = config
        self.app = FastAPI(title="MEV Bot Dashboard")
        self.active_connections: List[WebSocket] = []
        self.setup_routes()
        self.setup_middleware()

    def setup_middleware(self):
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    def setup_routes(self):
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            await websocket.accept()
            self.active_connections.append(websocket)
            try:
                while True:
                    await websocket.receive_text()
                    # Send real-time updates
                    await self.broadcast_metrics(websocket)
            except Exception:
                self.active_connections.remove(websocket)

        @self.app.get("/metrics")
        async def get_metrics():
            try:
                return JSONResponse(await self.get_system_metrics())
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/performance")
        async def get_performance():
            try:
                return JSONResponse(await self.get_performance_metrics())
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

    async def broadcast_metrics(self, websocket: WebSocket):
        """Send real-time metrics to connected clients"""
        metrics = await self.get_system_metrics()
        await websocket.send_json(metrics)

    async def get_system_metrics(self) -> Dict[str, Any]:
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "gas_price": await self.get_current_gas_price(),
            "profit": await self.get_total_profit(),
            "active_strategies": await self.get_active_strategies(),
            "execution_count": await self.get_execution_count()
        }

    async def get_performance_metrics(self) -> Dict[str, Any]:
        return {
            "total_profit": await self.get_total_profit(),
            "success_rate": await self.get_success_rate(),
            "average_execution_time": await self.get_avg_execution_time(),
            "gas_usage": await self.get_gas_usage()
        }

