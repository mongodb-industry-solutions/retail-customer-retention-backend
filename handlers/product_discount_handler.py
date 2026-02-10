import logging
import json
from typing import Dict, Any
from .base_handler import BaseNBAHandler
from bedrock import ask_llm
from mcp_server.server import mcp

logger = logging.getLogger(__name__)

class ProductDiscountAndRecommendationHandler(BaseNBAHandler):
    """
    Handler for search-friction signals → discount-product-recommendation NBA
    
    When users struggle to find what they're looking for, this handler creates
    a targeted response that combines:
    1. A discount offer tailored to their browsing behavior
    2. A single product recommendation based on inferred intent
    
    Flow:
    - Get session context (what they've been browsing)  
    - Generate discount message using LLM
    - Infer user intent using LLM
    - Find most relevant product via vector search
    - Combine into NBA for frontend display
    """
    
    async def process(self, signal_doc: Dict[str, Any]) -> Dict[str, Any]:
        signal_data = self.extract_signal_data(signal_doc)
        self.log_processing_start("search-friction", signal_data["uid"], signal_data["sid"])
        
        try:
            # Step 1: Get session context (browsing behavior, search queries, intent data)
            # This will return session_context["searchHistory"] and session_context["pastSignals"]
            session_context = await self._get_session_context(
                signal_data["uid"], 
                signal_data["sid"]
            )
            
            # Step 2A: Generate discount message based on session context
            # This creates the discount offer text shown to the user
            discount_message = await self._generate_discount_message(session_context)
            
            # Step 2B: Infer user intent for product search
            # This analyzes the context to understand what the user is actually looking for
            intent_summary = await self._infer_user_intent(session_context)
            
            # Step 3: Get single product recommendation using inferred intent
            # This finds the most relevant product to recommend based on the intent summary
            product_recommendation = await self._get_product_recommendation(intent_summary)
            
            # Step 4: Create the NBA combining discount + product recommendation
            result = await self._create_discount_product_nba(
                signal_data, 
                discount_message, 
                product_recommendation
            )
            
            self.log_processing_complete("search-friction")
            return result
            
        except Exception as e:
            logger.error(f"Error processing search-friction signal: {str(e)}", exc_info=True)
            raise
    
    async def _get_session_context(self, uid: str, sid: str) -> Dict[str, Any]:
        """
        Step 1: Retrieve comprehensive session context from multiple collections
        
        Aggregates data from:
        1. session_state.searchHistory - array of search query strings ["shoes", "running shoes"]
        2. session_signals - past behavioral signals (high-intent, search-friction, etc.)
        
        This complete context allows LLMs to understand both:
        - What specific terms the user has been searching for
        - What behavioral patterns they've exhibited
        
        Returns: Combined context dict with searchHistory (array) and pastSignals (array)
        """
        
        session_context = {
            "searchHistory": [],  # Array of search query strings
            "pastSignals": []
        }
        
        try:
            # Get search history from session_state collection
            logger.info(f"📞 Calling get_session_intent for search history - uid: {uid}, sid: {sid}")
            search_data = await mcp.call_tool("get_session_intent", {"uid": uid, "sid": sid})
            
            # Handle potential MCP wrapper response for search history
            if isinstance(search_data, list) and len(search_data) > 0:
                # Check if first item is TextContent wrapper
                first_item = search_data[0] 
                if hasattr(first_item, 'text'):
                    try:
                        search_data = json.loads(first_item.text)
                        logger.info(f"🔍 Parsed search data from TextContent: {search_data}")
                    except json.JSONDecodeError:
                        search_data = []
                        logger.warning("⚠️ Failed to parse search data JSON, using empty list")
            
            # Ensure search_data is a list of search query strings
            if isinstance(search_data, list):
                session_context["searchHistory"] = search_data
                logger.info(f"✅ Retrieved search history: {len(search_data)} queries")
            else:
                logger.warning(f"⚠️ Search data is not a list, got {type(search_data)}, using empty list")
                
        except Exception as e:
            logger.error(f"❌ Error calling get_session_intent: {e}")
            
        try:
            # Get past signals from session_signals collection  
            logger.info(f"📞 Calling get_session_signals for behavioral history - uid: {uid}, sid: {sid}")
            signals_data = await mcp.call_tool("get_session_signals", {"uid": uid, "sid": sid})
            
            # Handle potential MCP wrapper response for signals
            if isinstance(signals_data, list) and len(signals_data) > 0:
                # Check if it's wrapped in TextContent
                if hasattr(signals_data[0], 'text'):
                    try:
                        signals_data = json.loads(signals_data[0].text)
                        logger.info(f"🔍 Parsed signals data from TextContent")
                    except json.JSONDecodeError:
                        signals_data = []
                        logger.warning("⚠️ Failed to parse signals data JSON, using empty list")
            
            # Ensure signals_data is a list
            if isinstance(signals_data, list):
                session_context["pastSignals"] = signals_data
                logger.info(f"✅ Retrieved {len(signals_data)} past behavioral signals")
            else:
                logger.warning(f"⚠️ Signals data is not a list, got {type(signals_data)}")
                
        except Exception as e:
            logger.error(f"❌ Error calling get_session_signals: {e}")
            
        logger.info(f"🔍 Complete session context assembled - Search history: {bool(session_context['searchHistory'])}, Past signals: {len(session_context['pastSignals'])}")
        return session_context
    
    async def _generate_discount_message(self, session_context: Dict[str, Any]) -> Dict[str, str]:
        """
        Step 2A: Generate discount message using LLM
        
        Creates promotional text (title + message) based on the user's session data.
        The LLM analyzes what the user has been browsing to create targeted 
        discount offers specific to their interests (e.g. "10% off running shoes").
        
        Returns: {"title": "...", "message": "..."}
        """
        
        prompt = f"""
        Based on the following session context, generate a discount message:

        Session Context: {session_context}

        Generate:
        1) A title
        2) A message

        The message should:
        - Offer a discount (5-15%) or incentive
        - Be specific to a subcategory or article type
        - Create urgency and encourage action
        - Be concise and compelling

        Output as JSON:
        {{
            "title": "Brief attention-grabbing title",
            "message": "Specific discount message with subcategory/article type"
        }}
        """
        
        discount_raw = ask_llm(prompt)
        logger.info(f"Generated discount response: {discount_raw}")
        
        return self._parse_discount_response(discount_raw)
    
    async def _infer_user_intent(self, session_context: Dict[str, Any]) -> str:
        """
        Step 2B: Infer what the user is looking for using LLM
        
        Analyzes session context to understand the user's shopping intent.
        This creates a search query that will be used to find the most 
        relevant product to recommend alongside the discount.
        
        Example output: "User is looking for running shoes for women, size 8-9"
        """
        
        if not session_context:
            logger.warning("⚠️ No session context available for intent inference")
            return "General browsing intent"
        
        prompt = f"""
        Given the following session context, what is the user most likely looking for?

        Session Context: {session_context}

        Respond with:
        - A concise intent summary  
        - Relevant keywords or attributes that describe the intent

        Keep your response focused and actionable for product search.
        """
        
        intent_summary = ask_llm(prompt)
        logger.info(f"🎯 Inferred intent: {intent_summary}")
        return intent_summary
    
    def _parse_discount_response(self, discount_raw: Any) -> Dict[str, str]:
        """
        Parse and validate the LLM's discount message response
        
        Handles various response formats (JSON string, dict, markdown blocks) 
        and provides fallback if parsing fails.
        """
        
        try:
            if isinstance(discount_raw, str):
                cleaned_response = discount_raw.strip()
                if cleaned_response.startswith("```json"):
                    cleaned_response = cleaned_response.split("```json")[1].split("```")[0].strip()
                elif cleaned_response.startswith("```"):
                    cleaned_response = cleaned_response.split("```")[1].split("```")[0].strip()
                    
                discount = json.loads(cleaned_response)
            elif isinstance(discount_raw, dict):
                discount = discount_raw
            else:
                raise ValueError("Unexpected response format")
            
            # Validate required fields
            if "title" not in discount or "message" not in discount:
                raise ValueError("Missing required fields: title or message")
                
            logger.info(f"✅ Parsed discount - Title: {discount['title']}, Message: {discount['message']}")
            return discount
            
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.error(f"❌ Failed to parse discount response: {e}. Using fallback.")
            fallback = {
                "title": "Special Offer",
                "message": "Get 10% off your purchase today!"
            }
            logger.info(f"🔄 Using fallback discount: {fallback}")
            return fallback
    
    async def _get_product_recommendation(self, intent_summary: str) -> Dict[str, Any]:
        """
        Step 3: Get single product recommendation using vector search
        
        Uses the inferred user intent to find the most relevant product.
        Only returns the top matching product to show alongside the discount.
        
        Returns: Single product dict with {productId, name, imageUrl} or empty dict
        """
        
        try:
            products = await mcp.call_tool("vector_search_products", {"query": intent_summary})
            logger.info(f"📦 Found {len(products) if products else 0} products from search")
            
            # Get only the first (most relevant) product 
            if products and isinstance(products, list) and len(products) > 0:
                top_product = products[0]
                if isinstance(top_product, dict):
                    formatted_product = {
                        "productId": top_product.get("_id", ""),
                        "name": top_product.get("name", ""), 
                        "imageUrl": top_product.get("imageUrl", "")
                    }
                    logger.info(f"✅ Selected product recommendation: {formatted_product['name']}")
                    return formatted_product
                else:
                    logger.warning("Top product is not a valid dict")
                    return {}
            else:
                logger.warning("No products found or empty response")
                return {}
                
        except Exception as e:
            logger.error(f"❌ Error getting product recommendation: {e}")
            return {}
    
    async def _create_discount_product_nba(
        self, 
        signal_data: Dict[str, Any], 
        discount_message: Dict[str, str],
        product_recommendation: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Step 4: Create the final NBA combining discount + product recommendation
        
        Builds the NBA document that will be stored in the database and consumed 
        by the frontend to display the discount offer with a recommended product.
        
        NBA structure follows the specification:
        - type: "discount-product-recommendation"  
        - actionMetadata: contains display elements (title, message, product)
        """
        
        # Build the productRecommendation array for the NBA
        # If we have a product, include it; otherwise use empty array
        product_recommendations_array = [product_recommendation] if product_recommendation else []
        
        action = {
            "uid": signal_data["uid"],
            "sid": signal_data["sid"],
            "signalId": signal_data["signal_id"],
            "type": "discount-product-recommendation",
            "actionMetadata": {
                "title": discount_message["title"],
                "message": discount_message["message"],
                "productRecommendation": product_recommendations_array
            }
        }
        
        result = await mcp.call_tool("create_next_best_action", {"action": action})
        logger.info(f"✅ Created discount-product NBA result: {result}")
        return result