class ErrorCodes:
    # Authentication Errors
    AUTH_001 = "Invalid credentials"
    AUTH_002 = "Token expired"
    AUTH_003 = "Unauthorized access"

    # Trading Errors
    TRADE_001 = "Insufficient balance"
    TRADE_002 = "Invalid order size"
    TRADE_003 = "Price out of range"
    TRADE_004 = "Slippage exceeded"
    TRADE_005 = "Order not found"

    # Position Errors
    POS_001 = "Position not found"
    POS_002 = "Invalid leverage"
    POS_003 = "Liquidation risk"

    # System Errors
    SYS_001 = "Internal server error"
    SYS_002 = "Service unavailable"
    SYS_003 = "Database error"

class ErrorMessages:
    INSUFFICIENT_BALANCE = "Insufficient balance to complete the transaction"
    INVALID_ORDER_SIZE = f"Order size must be between {settings.MIN_ORDER_SIZE} and {settings.MAX_ORDER_SIZE}"
    PRICE_OUT_OF_RANGE = "Price is outside acceptable range"
    SLIPPAGE_EXCEEDED = "Slippage tolerance exceeded"
    ORDER_NOT_FOUND = "Order not found"
    POSITION_NOT_FOUND = "Position not found"
    INVALID_LEVERAGE = f"Leverage must not exceed {settings.MAX_LEVERAGE}"
    LIQUIDATION_RISK = "Position is at risk of liquidation"
    INTERNAL_ERROR = "An internal error occurred"

