class SuccessMessages:
    # Trading
    ORDER_CREATED = "Order created successfully"
    ORDER_CANCELLED = "Order cancelled successfully"
    TRADE_EXECUTED = "Trade executed successfully"
    POSITION_OPENED = "Position opened successfully"
    POSITION_CLOSED = "Position closed successfully"

    # Authentication
    LOGIN_SUCCESS = "Successfully logged in"
    LOGOUT_SUCCESS = "Successfully logged out"

class InfoMessages:
    # System Status
    SYSTEM_MAINTENANCE = "System under maintenance"
    MARKET_STATUS = "Market is {status}"
    
    # Trading Information
    ORDER_STATUS = "Order status: {status}"
    POSITION_STATUS = "Position status: {status}"
    
    # Notifications
    MARGIN_CALL = "Margin call warning for position {position_id}"
    LIQUIDATION_WARNING = "Liquidation warning for position {position_id}"

class ValidationMessages:
    INVALID_AMOUNT = "Invalid amount. Amount must be greater than {min_amount}"
    INVALID_PRICE = "Invalid price. Price must be between {min_price} and {max_price}"
    MIN_ORDER_SIZE = f"Order size must be greater than {settings.MIN_ORDER_SIZE}"
    MAX_ORDER_SIZE = f"Order size must be less than {settings.MAX_ORDER_SIZE}"
    MAX_LEVERAGE = f"Leverage must be less than {settings.MAX_LEVERAGE}"

