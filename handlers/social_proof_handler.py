import logging
import json
from typing import Dict, Any
from .base_handler import BaseNBAHandler
from bedrock import ask_llm
from mcp_server.server import mcp

logger = logging.getLogger(__name__)

class SocialProofHandler(BaseNBAHandler):
    """Handler for high-intent signals → social-proof-notification NBA"""
    
    async def process(self, signal_doc: Dict[str, Any]) -> Dict[str, Any]:
        signal_data = self.extract_signal_data(signal_doc)
        self.log_processing_start("high-intent", signal_data["uid"], signal_data["sid"])
        
        try:
            # Generate social proof message using LLM
            notification = await self._generate_social_proof_message(
                signal_data["evidence"], 
                signal_data["severity"]
            )
            
            # Create NBA
            result = await self._create_social_proof_nba(signal_data, notification)
            
            self.log_processing_complete("high-intent")
            return result
            
        except Exception as e:
            logger.error(f"Error processing high-intent signal: {str(e)}", exc_info=True)
            raise
    
    async def _generate_social_proof_message(self, evidence: str, severity: str) -> Dict[str, str]:
        """Generate social proof title and message using LLM"""
        
        prompt = f"""
        You are a Marketing UX writer and want to create a compelling social proof message.
        The customer showed a {severity} purchase intent based on the following evidence '{evidence}'.

        Make it engaging and persuasive.

        Output:
        - An object with the following format: {{ "title": "", "message": "" }}
        - title: short title for the social proof notification
        - message: short description for the social proof notification, take the subCategory provided inside the evidence to tailor this.

        The message should:
        - Be concise and compelling
        - Create urgency or social validation
        - Encourage immediate action
        - Should NOT include any discounts. But you can add analytics like amount of people interested in that category, etc...
        - Try to keep shorter than 25 words.

        The title should be:
        - Short and attention-grabbing
        - For example: "Popular Right Now", "Good Choice", "[The category] are moving"

        Example output:
        {{
            "title": "Popular pick!",
            "message": "Five customers completed a purchase in Shoes recently. You're looking in the right place."
        }}
        """
        
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
        
        prompt = f"""
        Generate a short, compelling pressure message to encourage purchase of a product.
        
        The message should create urgency or social pressure such as:
        - "X people purchased this in the last Y days"
        - "This item is trending"  
        - "Only few units left"
        - "High demand item"
        - "Popular choice this week"
        
        Requirements:
        - Keep it under 15 words
        - Make it feel authentic and believable
        - Create urgency without being pushy
        - Don't mention specific numbers unless they sound realistic
        
        Just return the message text, no JSON formatting needed.
        """
        
        pressure_message = ask_llm(prompt)
        logger.info(f"Generated product pressure message: {pressure_message}")
        
        # Clean up any extra formatting
        if isinstance(pressure_message, str):
            cleaned_message = pressure_message.strip().strip('"').strip("'")
            return cleaned_message
        else:
            # Fallback message
            return "Trending item"
    
    async def _create_social_proof_nba(self, signal_data: Dict[str, Any], notification: Dict[str, str]) -> Dict[str, Any]:
        """Create social proof NBA"""
        
        action = {
            "uid": signal_data["uid"],
            "sid": signal_data["sid"], 
            "signalId": signal_data["signal_id"],
            "type": "social-proof-notification",
            "actionMetadata": {
                "title": notification["title"],
                "message": notification["message"]
            }
        }
        
        # Add embedInProduct object if product_id exists
        if signal_data["product_id"]:
            pressure_message = await self._generate_product_pressure_message(signal_data["product_id"])
            action["embedInProduct"] = {
                "productId": signal_data["product_id"],
                "message": pressure_message
            }
        
        result = await mcp.call_tool("create_next_best_action", {"action": action})
        logger.info(f"✅ Created social proof NBA result: {result}")
        return result