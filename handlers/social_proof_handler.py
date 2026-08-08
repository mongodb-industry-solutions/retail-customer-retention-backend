import logging
import json
from typing import Dict, Any
from .base_handler import BaseNBAHandler
from bedrock import ask_llm
from mcp_server.server import mcp
from prompts import SOCIAL_PROOF_MESSAGE_PROMPT, PRODUCT_PRESSURE_MESSAGE_PROMPT

logger = logging.getLogger(__name__)

class SocialProofHandler(BaseNBAHandler):
    """Handler for high-intent signals → social-proof-notification NBA"""
    
    async def process(self, signal_doc: Dict[str, Any]) -> Dict[str, Any]:
        signal_data = self.extract_signal_data(signal_doc)
        self.log_processing_start("high-intent", signal_data["uid"], signal_data["sid"])
        
        conversation_log = []
        
        try:
            # Get product data using MCP tool
            high_intent_product = None
            if signal_data.get("product_id"):
                product_result = await mcp.call_tool("search_product_by_id", {"product_id": signal_data["product_id"]})
                
                # Parse the MCP tool response which returns TextContent objects
                if product_result and isinstance(product_result, list) and len(product_result) > 0:
                    # Extract JSON text from TextContent object
                    text_content = product_result[0]
                    if hasattr(text_content, 'text'):
                        try:
                            high_intent_product = json.loads(text_content.text)
                            logger.info(f"Parsed product data: {high_intent_product}")
                        except json.JSONDecodeError as e:
                            logger.error(f"Failed to parse product JSON: {e}")
                            high_intent_product = None
                    else:
                        logger.error(f"Unexpected MCP response format: {product_result}")
                else:
                    logger.warning(f"No product data returned for product_id: {signal_data['product_id']}")
            
            conversation_log.append({
                "step": "product_lookup",
                "description": "Looked up high-intent product",
                "data": {"productId": signal_data.get("product_id"), "found": high_intent_product is not None}
            })
            
            # Generate social proof message using LLM
            notification = await self._generate_social_proof_message(
                signal_data["evidence"], 
                signal_data["severity"],
                high_intent_product
            )
            conversation_log.append({
                "step": "social_proof_generation",
                "description": "LLM generated social proof notification",
                "data": notification
            })
            
            # Create NBA
            result = await self._create_social_proof_nba(signal_data, notification, conversation_log)
            
            self.log_processing_complete("high-intent")
            return result
            
        except Exception as e:
            logger.error(f"Error processing high-intent signal: {str(e)}", exc_info=True)
            raise
    
    async def _generate_social_proof_message(self, evidence: str, severity: str, high_intent_product: Dict[str, Any] = None) -> Dict[str, str]:
        """Generate social proof title and message using LLM"""
        
        product_info = ""
        if high_intent_product and not high_intent_product.get("error"):
            product_name = high_intent_product.get("name", "")
            product_category = high_intent_product.get("subCategory", high_intent_product.get("articleType", ""))
            product_type = high_intent_product.get("articleType", "")
            product_info = f"Product details: {product_name} of type {product_type} in {product_category} category."
        
        prompt = SOCIAL_PROOF_MESSAGE_PROMPT.format(
            severity=severity,
            evidence=evidence,
            product_info=product_info
        )
        
        notification_raw = ask_llm(prompt)
        logger.info(f"Generated raw response: {notification_raw}")
        
        return self._parse_llm_response(notification_raw)
    
    def _parse_llm_response(self, notification_raw: Any) -> Dict[str, str]:
        """Parse and validate LLM response"""
        
        try:
            # Try to parse as JSON if it's a string
            if isinstance(notification_raw, str):
                # Remove any markdown code blocks if present
                cleaned_response = notification_raw.strip()
                if cleaned_response.startswith("```json"):
                    cleaned_response = cleaned_response.split("```json")[1].split("```")[0].strip()
                elif cleaned_response.startswith("```"):
                    cleaned_response = cleaned_response.split("```")[1].split("```")[0].strip()
                
                notification = json.loads(cleaned_response)
            elif isinstance(notification_raw, dict):
                notification = notification_raw
            else:
                raise ValueError("Unexpected response format")
            
            # Validate required fields
            if not isinstance(notification, dict):
                raise ValueError("Response is not a dictionary")
            
            # Ensure title and message exist
            if "title" not in notification or "message" not in notification:
                raise ValueError("Missing required fields: title or message")
                
            logger.info(f"✅ Parsed notification - Title: {notification['title']}, Message: {notification['message']}")
            return notification
            
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.error(f"❌ Failed to parse LLM response: {e}. Using fallback.")
            # Fallback notification
            fallback = {
                "title": "Popular Choice!",
                "message": "A few shoppers made a purchase in the last 24 hours."
            }
            logger.info(f"🔄 Using fallback notification: {fallback}")
            return fallback
    
    async def _generate_product_pressure_message(self, product_id: str) -> str:
        """Generate pressure message for specific product using LLM"""
        
        prompt = PRODUCT_PRESSURE_MESSAGE_PROMPT
        
        pressure_message = ask_llm(prompt)
        logger.info(f"Generated product pressure message: {pressure_message}")
        
        # Clean up any extra formatting
        if isinstance(pressure_message, str):
            cleaned_message = pressure_message.strip().strip('"').strip("'")
            return cleaned_message
        else:
            # Fallback message
            return "Trending item"
    
    async def _create_social_proof_nba(self, signal_data: Dict[str, Any], notification: Dict[str, str], conversation_log: list = None) -> Dict[str, Any]:
        """Create social proof NBA"""
        
        action = {
            "uid": signal_data["uid"],
            "sid": signal_data["sid"], 
            "type": "social-proof-notification",
            "actionMetadata": {
                "title": notification["title"],
                "message": notification["message"],
                "triggeredBySignal": f"{signal_data['severity']}_{signal_data['signal']}",
            }
        }
        
        # Add embedInProduct object if product_id exists
        if signal_data["product_id"]:
            pressure_message = await self._generate_product_pressure_message(signal_data["product_id"])
            action["embedInProduct"] = {
                "productId": signal_data["product_id"],
                "message": pressure_message
            }
            if conversation_log is not None:
                conversation_log.append({
                    "step": "product_pressure",
                    "description": "LLM generated product pressure message",
                    "data": {"productId": signal_data["product_id"], "message": pressure_message}
                })
        
        if conversation_log:
            action["agentConversation"] = conversation_log
        
        result = await mcp.call_tool("create_next_best_action", {"action": action})
        logger.info(f"✅ Created social proof NBA result: {result}")
        return result