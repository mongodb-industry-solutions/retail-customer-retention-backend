from mcp_server.server import mcp  # Import the single mcp instance shared across your project  
import random

@mcp.tool(
    name="discount_message",
    description="Discount message generator based on business logic"
)
def discount_message(severity: str) -> dict:
    severity_config = {
        "low": {
            "titles": ["Before you go", "Wait a moment"],
            "messages": [
                "Get 5% off your shipping if you complete your purchase today.",
                "Save 5% on shipping costs when you finish your order."
            ]
        },
        "medium": {
            "titles": ["Don't miss out", "Limited time offer"],
            "messages": [
                "Complete your order now and get 15% off shipping.",
                "Finish your purchase today and save 15% on shipping costs."
            ]
        },
        "high": {
            "titles": ["Wait! Special offer", "Exclusive deal"],
            "messages": [
                "Complete your order now and get 50% off shipping!",
                "Huge savings: 50% off shipping if you complete your purchase now."
            ]
        },
        "urgent": {
            "titles": ["Last chance", "Final offer"],
            "messages": [
                "Complete your order now and get FREE shipping!",
                "Don't wait - finish your purchase and enjoy FREE shipping!"
            ]
        }
    }
    
    # Get config for severity, default to 'low' if not found
    config = severity_config.get(severity, severity_config["low"])
    
    # Randomly select title and message
    selected_title = random.choice(config["titles"])
    selected_message = random.choice(config["messages"])
    
    result = {
        "title": selected_title,
        "message": selected_message
    }
    
    print(f"DEBUG: Returning from shipping discount_message (severity: {severity}): {result}, type: {type(result)}")
    return result
