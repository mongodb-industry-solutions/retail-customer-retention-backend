import logging
import json
from typing import Dict, Any
from .base_handler import BaseNBAHandler
from bedrock import ask_llm
from mcp_server.server import mcp
from prompts import DISCOUNT_MESSAGE_PROMPT, INTENT_INFERENCE_PROMPT

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
        logger.info("🚀 Starting ProductDiscountAndRecommendationHandler.process")
        signal_data = self.extract_signal_data(signal_doc)
        self.log_processing_start("search-friction", signal_data["uid"], signal_data["sid"])
        
        # Collect agent conversation steps for storage
        conversation_log = []
        
        try:
            # Step 1: Get session context (browsing behavior, search queries, intent data)
            # This will return session_context["searchHistory"] and session_context["pastSignals"]
            session_context = await self._get_session_context(
                signal_data["uid"], 
                signal_data["sid"]
            )
            conversation_log.append({
                "step": "session_context",
                "description": "Retrieved session browsing context",
                "data": {
                    "searchHistory": session_context.get("searchHistory", []),
                    "signalCount": len(session_context.get("pastSignals", []))
                }
            })
            
            # Step 2A: Generate discount message based on session context
            # This creates the discount offer text shown to the user
            discount_message = await self._generate_discount_message(session_context)
            conversation_log.append({
                "step": "discount_generation",
                "description": "LLM generated discount offer",
                "data": discount_message
            })
            
            # Step 2B: Infer user intent for product search
            # This analyzes the context to understand what the user is actually looking for
            intent_summary = await self._infer_user_intent(session_context)
            conversation_log.append({
                "step": "intent_inference",
                "description": "LLM inferred user shopping intent",
                "data": {"intentSummary": intent_summary[:500] if intent_summary else ""}
            })
            
            # Step 3: Get single product recommendation using inferred intent
            # This finds the most relevant product to recommend based on the intent summary
            product_recommendation = await self._get_product_recommendation(intent_summary)
            conversation_log.append({
                "step": "product_recommendation",
                "description": "Vector search found matching product",
                "data": product_recommendation if product_recommendation else {"result": "none"}
            })
            
            # Step 4: Create the NBA combining discount + product recommendation
            result = await self._create_discount_product_nba(
                signal_data, 
                discount_message, 
                product_recommendation,
                conversation_log
            )
            
            self.log_processing_complete("search-friction")
            return result
            
        except Exception as e:
            logger.error(f"Error processing search-friction signal: {str(e)}", exc_info=True)
            raise
    
    async def _get_session_context(self, uid: str, sid: str) -> Dict[str, Any]:
        """Retrieve session context from search history and behavioral signals"""
        logger.info(f"📋 Getting session context for uid: {uid}, sid: {sid}")
        
        session_context = {"searchHistory": [], "pastSignals": []}
        
        try:
            search_data = await mcp.call_tool("get_session_search_history", {"uid": uid, "sid": sid})
            session_context["searchHistory"] = self._parse_mcp_response(search_data, list)
        except Exception as e:
            logger.error(f"Error calling get_session_search_history: {e}")
            
        try:
            signals_data = await mcp.call_tool("get_session_signals", {"uid": uid, "sid": sid})
            session_context["pastSignals"] = self._parse_mcp_response(signals_data, list)
        except Exception as e:
            logger.error(f"Error calling get_session_signals: {e}")
            
        return session_context
    
    async def _generate_discount_message(self, session_context: Dict[str, Any]) -> Dict[str, str]:
        """Generate discount message using LLM"""
        logger.info("💰 Generating discount message")
        
        prompt = DISCOUNT_MESSAGE_PROMPT.format(session_context=session_context)
        
        discount_raw = ask_llm(prompt)
        return self._parse_discount_response(discount_raw)
    
    async def _infer_user_intent(self, session_context: Dict[str, Any]) -> str:
        """Infer what the user is looking for using algorithmic analysis + LLM"""
        logger.info(f"🎯 Starting user intent inference with session context: {session_context}")
        
        search_history = session_context.get("searchHistory", [])
        past_signals = session_context.get("pastSignals", [])
        
        # Only return early if we have NO useful data at all
        if not search_history and not past_signals:
            logger.info("❌ No search history or signals available")
            return "General browsing intent"
        
        try:
            patterns_raw = await mcp.call_tool("analyze_session_intent_patterns", {
                "search_history": search_history,
                "past_signals": past_signals
            })
            
            patterns = self._parse_mcp_response(patterns_raw, dict)
            
            # Step 2: Create structured LLM prompt using analysis results
            intent_insights = patterns.get('intent_insights', {})
            prompt = INTENT_INFERENCE_PROMPT.format(
                recent_focus=patterns.get('recent_focus', []),
                search_clusters=patterns.get('search_clusters', []),
                has_size_mentions=intent_insights.get('has_size_mentions', False),
                dominant_topic_dimension=intent_insights.get('dominant_topic_dimension', ''),
                behavioral_indicators=intent_insights.get('behavioral_indicators', [])
            )
            
            # Step 3: Get LLM inference based on structured analysis
            logger.info(f"🎯 Sending prompt to LLM:\n{prompt}")
            intent_summary = ask_llm(prompt)
            logger.info(f"🎯 Final intent summary: {intent_summary}")
            
            # Fallback to algorithmic recommendation if LLM fails
            if not intent_summary or len(intent_summary.strip()) < 10:
                fallback_query = patterns.get('recommended_search_query', '')
                return fallback_query if fallback_query else "General browsing intent"
            
            return intent_summary
            
        except Exception as e:
            logger.info(f"⚠️ Exception in intent inference: {e}")
            # Fallback to simple recent search
            if search_history:
                return search_history[-1]
            return "General browsing intent"
    
    def _parse_discount_response(self, discount_raw: Any) -> Dict[str, str]:
        """
        Parse and validate the LLM's discount message response
        
        Handles various response formats (JSON string, dict, markdown blocks) 
        and provides fallback if parsing fails.
        """
        logger.info("🔍 Parsing discount response")
        
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
                
            logger.info(f"✅ Parsed discount")
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
        """Get single product recommendation using vector search"""
        logger.info(f"🛍️ Getting product recommendation for intent: {intent_summary}")
        
        try:
            products = await mcp.call_tool("vector_search_products", {"query": intent_summary})
            
            if products and isinstance(products, list) and len(products) > 0:
                top_product = self._parse_mcp_response(products[0])
                
                if isinstance(top_product, dict):
                    formatted_product = {
                        "productId": top_product.get("_id", ""),
                        "name": top_product.get("name", ""), 
                        "imageUrl": top_product.get("image", {}).get("url", "") if isinstance(top_product.get("image"), dict) else ""
                    }
                    return formatted_product
            return {}
                
        except Exception as e:
            logger.error(f"Error getting product recommendation: {e}")
            return {}
    
    def _parse_mcp_response(self, response, expected_type=None):
        """Helper to parse MCP TextContent responses"""
        logger.info(f"🔧 Parsing MCP response: {response}")
        if hasattr(response, 'text'):
            try:
                import json
                return json.loads(response.text)
            except (json.JSONDecodeError, AttributeError) as e:
                logger.info(f"⚠️ Exception parsing response.text: {e}")
                return expected_type() if expected_type else response.text
        elif isinstance(response, list) and response and hasattr(response[0], 'text'):
            # Handle list of TextContent objects - parse ALL of them
            parsed_list = []
            json_failed = False
            
            for item in response:
                if hasattr(item, 'text') and item.text:
                    try:
                        import json
                        # Try JSON parsing first
                        parsed_item = json.loads(item.text)
                        parsed_list.append(parsed_item)
                    except (json.JSONDecodeError, AttributeError):
                        # If JSON fails, use raw text (for search queries like "cream")
                        parsed_list.append(item.text)
                        json_failed = True
            
            if json_failed:
                logger.info(f"📝 Parsed {len(parsed_list)} plain text items from TextContent list")
            else:
                logger.info(f"📋 Parsed {len(parsed_list)} JSON items from TextContent list")
            
            # Use expected_type to determine return format
            if expected_type == dict and len(parsed_list) == 1:
                logger.info("🎯 Expected dict + single item - returning dict directly") 
                return parsed_list[0]
            elif expected_type == list:
                logger.info(f"📊 Expected list - returning list of {len(parsed_list)} items")
                return parsed_list
            else:
                # No expected_type provided, use smart default
                if len(parsed_list) == 1:
                    logger.info("🎯 No expected_type + single item - returning dict directly")
                    return parsed_list[0]
                else:
                    logger.info(f"📊 No expected_type + multiple items - returning list of {len(parsed_list)} items")
                    return parsed_list
        return response if response is not None else (expected_type() if expected_type else "")
    
    async def _create_discount_product_nba(self, signal_data: Dict[str, Any], discount_message: Dict[str, str], product_recommendation: Dict[str, Any], conversation_log: list = None) -> Dict[str, Any]:
        """Create the final NBA combining discount + product recommendation"""
        logger.info("📝 Creating discount-product NBA")
        
        action = {
            "uid": signal_data["uid"],
            "sid": signal_data["sid"],
            "type": "discount-product-recommendation",
            "actionMetadata": {
                "title": discount_message["title"],
                "message": discount_message["message"],
                "productRecommendation": product_recommendation if product_recommendation else None,
                "triggeredBySignal": f"{signal_data['severity']}_{signal_data['signal']}",
            },
        }
        
        # Store the agent conversation/reasoning chain for UI display
        if conversation_log:
            action["agentConversation"] = conversation_log
        
        result = await mcp.call_tool("create_next_best_action", {"action": action})
        logger.info(f"✅ Created discount-product NBA result: {result}")
        return result
