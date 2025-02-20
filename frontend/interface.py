from fastapi import FastAPI, WebSocket, HTTPException, Depends, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from fastapi.responses import JSONResponse
from typing import Dict, Any, List, Optional
import logging
import asyncio
from datetime import datetime

# Import core components
from app.core.strategy_executor import StrategyExecutor
from app.core.security_manager import SecurityManager
from app.core.risk_manager import RiskManager
from app.core.monitoring import MonitoringSystem
from app.core.alert_system import AlertSystem

logger = logging.getLogger(__name__)

class APIInterface:
    def __init__(self, config: Dict[str, Any]):
        self.app = FastAPI(title="MEV Bot API", version="1.0.0")
        self.config = config
        self.active_connections: List[WebSocket] = []
        
        # Initialize core components
        self.strategy_executor = StrategyExecutor(config)
        self.security_manager = SecurityManager(config)
        self.risk_manager = RiskManager(config)
        self.monitoring = MonitoringSystem(config)
        self.alert_system = AlertSystem(config)
        
        # Setup middleware
        self._setup_middleware()
        # Setup routes
        self._setup_routes()

    def _setup_middleware(self):
        """Configure middleware"""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=self.config.get("allowed_origins", ["*"]),
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    def _setup_routes(self):
        """Setup API routes"""
        
        @self.app.get("/health")
        async def health_check():
            return {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat()
            }

        @self.app.get("/api/v1/metrics")
        async def get_metrics():
            try:
                metrics = await self.monitoring.get_metrics()
                return JSONResponse(content=metrics)
            except Exception as e:
                logger.error(f"Failed to get metrics: {str(e)}")
                raise HTTPException(status_code=500, detail="Failed to fetch metrics")

        @self.app.post("/api/v1/strategies/{strategy_id}/execute")
        async def execute_strategy(strategy_id: str, params: Dict[str, Any]):
            try:
                # Validate risk parameters
                risk_assessment = await self.risk_manager.assess_risk(strategy_id, params)
                if not risk_assessment["approved"]:
                    raise HTTPException(status_code=400, detail=risk_assessment["reason"])
                
                # Execute strategy
                result = await self.strategy_executor.execute_strategy(strategy_id, params)
                return JSONResponse(content=result)
            except Exception as e:
                logger.error(f"Strategy execution failed: {str(e)}")
                raise HTTPException(status_code=500, detail="Strategy execution failed")

        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            await self._handle_websocket_connection(websocket)

    async def _handle_websocket_connection(self, websocket: WebSocket):
        """Handle WebSocket connections"""
        await websocket.accept()
        self.active_connections.append(websocket)
        
        try:
            while True:
                # Get real-time metrics
                metrics = await self.monitoring.get_real_time_metrics()
                await websocket.send_json(metrics)
                await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"WebSocket error: {str(e)}")
        finally:
            self.active_connections.remove(websocket)
            await websocket.close()

    async def broadcast_update(self, data: Dict[str, Any]):
        """Broadcast updates to all connected clients"""
        for connection in self.active_connections:
            try:
                await connection.send_json(data)
            except Exception as e:
                logger.error(f"Failed to broadcast update: {str(e)}")
                self.active_connections.remove(connection)

    async def start(self):
        """Start the API interface"""
        try:
            logger.info("Starting API interface...")
            await self.monitoring.start()
            await self.alert_system.start()
            logger.info("API interface started successfully")
        except Exception as e:
            logger.error(f"Failed to start API interface: {str(e)}")
            raise

    async def stop(self):
        """Stop the API interface"""
        try:
            logger.info("Stopping API interface...")
            for connection in self.active_connections:
                await connection.close()
            self.active_connections.clear()
            await self.monitoring.stop()
            await self.alert_system.stop()
            logger.info("API interface stopped successfully")
        except Exception as e:
            logger.error(f"Failed to stop API interface: {str(e)}")
            raise

# Initialize the API interface
def create_api(config: Dict[str, Any]) -> FastAPI:
    api = APIInterface(config)
    return api.app

