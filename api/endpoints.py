from typing import Dict, Any, Optional
import logging
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

app = FastAPI(title="MEV Bot API", version="1.0.0")
security = HTTPBearer()
logger = logging.getLogger(__name__)

class APIEndpoints:
    def __init__(self, strategy_executor, monitoring_system, config_manager):
        self.strategy_executor = strategy_executor
        self.monitoring = monitoring_system
        self.config = config_manager
        self.setup_routes()

    def setup_routes(self):
        @app.post("/strategy/execute")
        async def execute_strategy(
            strategy_name: str,
            strategy_params: Dict[str, Any],
            background_tasks: BackgroundTasks,
            credentials: HTTPAuthorizationCredentials = Depends(security)
        ):
            try:
                # Validate authentication
                if not await self._validate_auth(credentials.credentials):
                    raise HTTPException(status_code=401, detail="Invalid authentication")

                # Execute strategy
                execution_id = await self.strategy_executor.execute_strategy(
                    strategy_name,
                    strategy_params
                )

                return JSONResponse({
                    "status": "success",
                    "execution_id": execution_id,
                    "message": f"Strategy {strategy_name} execution initiated"
                })

            except Exception as e:
                logger.error(f"Strategy execution failed: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))

        @app.get("/strategy/status/{execution_id}")
        async def get_execution_status(
            execution_id: str,
            credentials: HTTPAuthorizationCredentials = Depends(security)
        ):
            try:
                status = await self.strategy_executor.get_execution_status(execution_id)
                if not status:
                    raise HTTPException(status_code=404, detail="Execution not found")
                return JSONResponse(status)
            except Exception as e:
                logger.error(f"Failed to get execution status: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))

        @app.get("/metrics")
        async def get_metrics(
            credentials: HTTPAuthorizationCredentials = Depends(security)
        ):
            try:
                metrics = await self.monitoring.get_system_metrics()
                return JSONResponse(metrics)
            except Exception as e:
                logger.error(f"Failed to get metrics: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))

        @app.post("/config/update")
        async def update_config(
            config_updates: Dict[str, Any],
            credentials: HTTPAuthorizationCredentials = Depends(security)
        ):
            try:
                if not await self._validate_admin_auth(credentials.credentials):
                    raise HTTPException(status_code=403, detail="Admin access required")
                
                success = await self.config.update_config(config_updates)
                if not success:
                    raise HTTPException(status_code=400, detail="Failed to update config")
                
                return JSONResponse({
                    "status": "success",
                    "message": "Configuration updated successfully"
                })
            except Exception as e:
                logger.error(f"Config update failed: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))

        @app.get("/system/health")
        async def health_check():
            try:
                health_status = await self.monitoring.get_health_status()
                return JSONResponse(health_status)
            except Exception as e:
                logger.error(f"Health check failed: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))

        @app.get("/active-executions")
        async def get_active_executions(
            credentials: HTTPAuthorizationCredentials = Depends(security)
        ):
            try:
                executions = await self.strategy_executor.get_active_executions()
                return JSONResponse({
                    "active_executions": executions,
                    "count": len(executions)
                })
            except Exception as e:
                logger.error(f"Failed to get active executions: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))

    async def _validate_auth(self, token: str) -> bool:
        # Implement your authentication logic here
        return True

    async def _validate_admin_auth(self, token: str) -> bool:
        # Implement your admin authentication logic here
        return True

# Initialize and run the API
def create_app(
    strategy_executor,
    monitoring_system,
    config_manager
) -> FastAPI:
    APIEndpoints(strategy_executor, monitoring_system, config_manager)
    return app

