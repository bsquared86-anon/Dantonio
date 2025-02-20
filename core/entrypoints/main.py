# app/main.py
import asyncio
import logging
from fastapi import FastAPI
from app.core.strategy.strategy_manager import StrategyManager
from app.core.performance_monitor import PerformanceMonitor
from app.core.config_manager import ConfigManager
from app.core.logging_system import LoggingSystem
from app.core.alert_system import AlertSystem
from app.api.routes import router as api_router
from app.api.websockets import router as ws_router

class MEVBot:
    def __init__(self):
        self.app = FastAPI(title="MEV Bot", version="1.0.0")
        self.logger = logging.getLogger(__name__)
        self.setup_routes()
        
    def setup_routes(self):
        self.app.include_router(api_router, prefix="/api")
        self.app.include_router(ws_router, prefix="/ws")

    async def startup(self):
        try:
            # Initialize core components
            self.config_manager = ConfigManager()
            await self.config_manager.initialize()

            self.logging_system = LoggingSystem()
            await self.logging_system.initialize()

            self.alert_system = AlertSystem(self.config_manager)
            await self.alert_system.initialize()

            self.performance_monitor = PerformanceMonitor(
                self.config_manager,
                self.logging_system
            )
            await self.performance_monitor.initialize()

            self.strategy_manager = StrategyManager(
                self.config_manager,
                self.performance_monitor,
                self.alert_system,
                self.logging_system
            )
            await self.strategy_manager.initialize()

            self.logger.info("MEV Bot initialized successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize MEV Bot: {str(e)}")
            return False

    async def shutdown(self):
        try:
            await self.strategy_manager.cleanup()
            await self.performance_monitor.cleanup()
            await self.alert_system.cleanup()
            await self.logging_system.cleanup()
            self.logger.info("MEV Bot shutdown completed")
        except Exception as e:
            self.logger.error(f"Error during shutdown: {str(e)}")

app = MEVBot().app

@app.on_event("startup")
async def startup_event():
    await app.state.bot.startup()

@app.on_event("shutdown")
async def shutdown_event():
    await app.state.bot.shutdown()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

async def main():
    # Initialize components
    config_manager = ConfigManager()
    web3 = Web3(Web3.HTTPProvider(config_manager.get('network.rpc_url')))
    
    # Initialize security and monitoring
    security_manager = SecurityManager(config_manager, web3)
    monitoring = MonitoringSystem(config_manager)
    
    # Start monitoring
    await monitoring.start_monitoring()
    
    # In your trading loop
    while True:
        try:
            # Validate security before trade
            tx_data = prepare_transaction()
            if not await security_manager.validate_transaction(tx_data):
                continue
                
            # Check balance
            if not await security_manager.check_balance():
                await monitoring._send_alert({
                    "message": "Emergency shutdown: Low balance",
                    "severity": "CRITICAL"
                })
                break
                
            # Execute trade and record metrics
            start_time = time.time()
            trade_result = await execute_trade(tx_data)
            execution_time = time.time() - start_time
            
            # Record trade metrics
            await monitoring.record_trade({
                "success": trade_result.success,
                "profit": trade_result.profit,
                "gas_used": trade_result.gas_used,
                "execution_time": execution_time
            })
            
        except Exception as e:
            logging.error(f"Trading error: {str(e)}")
            await monitoring._send_alert({
                "message": f"Trading error: {str(e)}",
                "severity": "ERROR"
            })

