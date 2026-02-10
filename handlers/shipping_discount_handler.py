import logging
import json
from typing import Dict, Any
from .base_handler import BaseNBAHandler
from mcp_server.server import mcp

logger = logging.getLogger(__name__)

class ShippingDiscountHandler(BaseNBAHandler):
    """Handler for exit-risk signals → shipping-discount NBA"""
    
    async def process(self, signal_doc: Dict[str, Any]) -> Dict[str, Any]:
        signal_data = self.extract_signal_data(signal_doc)
        self.log_processing_start("exit-risk", signal_data["uid"], signal_data["sid"])
        
        try:
            # Use MCP tool for consistency
            discount_message = await self._get_discount_message(signal_data["severity"])
            
            # Create NBA
            result = await self._create_shipping_discount_nba(signal_data, discount_message)
            
            self.log_processing_complete("exit-risk")
            return result
            
        except Exception as e:
            logger.error(f"Error processing exit-risk signal: {str(e)}", exc_info=True)
            raise
    
    async def _get_discount_message(self, severity: str) -> Dict[str, str]:
        """Get discount message using MCP tool"""
        
        try:
            discount_response = await mcp.call_tool("discount_message", {"severity": severity})
            logger.info(f"🔍 DEBUG: discount_response type: {type(discount_response)}, value: {discount_response}")
            
            # Handle if MCP wraps the response in a list with TextContent
            if isinstance(discount_response, list) and len(discount_response) > 0:
                first_item = discount_response[0]
                logger.info(f"🔍 DEBUG: Extracted from list, discount type: {type(first_item)}, value: {first_item}")
                
                # Check if it's a TextContent object and parse the JSON
                if hasattr(first_item, 'text'):
                    try:
                        discount = json.loads(first_item.text)
                        logger.info(f"🔍 DEBUG: Parsed JSON successfully: {discount}")
                    except json.JSONDecodeError as e:
                        logger.error(f"❌ Failed to parse JSON from TextContent: {e}")
                        discount = {"title": "Special Discount", "message": "Error parsing discount"}
                else:
                    discount = first_item
            else:
                discount = discount_response
                logger.info(f"🔍 DEBUG: Using direct response, discount type: {type(discount)}, value: {discount}")
            
            logger.info(f"💰 Selected discount message - Title: {discount['title']}, Message: {discount['message']}")
            return discount
            
        except Exception as e:
            logger.error(f"❌ Error calling discount_message tool: {e}")
            # Fallback message
            fallback = {
                "title": "Before you go",
                "message": "Enjoy free shipping if you complete your purchase today."
            }
            logger.info(f"🔄 Using fallback discount: {fallback}")
            return fallback
    
    async def _create_shipping_discount_nba(
        self, 
        signal_data: Dict[str, Any], 
        discount_message: Dict[str, str]
    ) -> Dict[str, Any]:
        """Create shipping discount NBA"""
        
        action = {
            "uid": signal_data["uid"],
            "sid": signal_data["sid"],
            "signalId": signal_data["signal_id"], 
            "type": "shipping-discount",
            "actionMetadata": {
                "title": discount_message["title"],
                "message": discount_message["message"]
            }
        }
        
        result = await mcp.call_tool("create_next_best_action", {"action": action})
        logger.info(f"✅ Created shipping discount NBA result: {result}")
        return result