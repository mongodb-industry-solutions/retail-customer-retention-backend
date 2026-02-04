from mcp_server.server import mcp  # Import the single mcp instance shared across your project  

@mcp.tool(
    name="discount_message",
    description="Discount message generator based on business logic"
)
def discount_message(severity: str) -> dict:
    severity_config = {
        "low": {
            "title": "Special Offer",
            "message": "Get 5% off your order today!"
        },
        "medium": {
            "title": "Limited Time Deal",
            "message": "Don't miss out - 15% off expires soon!"
        },
        "high": {
            "title": "Wait! Exclusive Discount",
            "message": "Last chance for 25% off your entire order!"
        }
    }
    
    result = severity_config.get(severity, {
        "title": "Special Discount",
        "message": f"Discount message for severity '{severity}'"
    })
    
    print(f"DEBUG: Returning from discount_message: {result}, type: {type(result)}")
    return result
