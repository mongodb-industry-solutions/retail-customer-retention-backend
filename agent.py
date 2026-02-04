import logging
from bedrock import ask_llm
from mcp_server.server import mcp

logger = logging.getLogger(__name__)

async def handle_signal(doc: dict):
    logger.info(f"🔄 Processing signal from document: {doc.get('_id', 'unknown')}")
    
    try:
        signal = doc.get("signal")
        logger.info(f"Signal type: {signal}")
        
        if not signal:
            logger.warning("Document missing 'signal' field")
            return
        
        uid = doc.get("uid")
        sid = doc.get("sid")
        logger.info(f"👤 Processing for user: {uid}, session: {sid}")

        if signal == "high-intent":
            logger.info("🎯 Processing high-intent signal...")
            evidence = doc.get('evidence', 'No evidence provided')
            logger.debug(f"Evidence: {evidence}")
            
            message = ask_llm(
                f"Write a short social proof message based on: {evidence}"
            )
            logger.info(f"Generated message: {message}")

            result = await mcp.call_tool(
                "create_next_best_action",
                {
                    "action": {
                        "uid": uid,
                        "sid": sid,
                        "type": "social-proof-notification",
                        "actionMetadata": {
                            "title": "Popular pick!",
                            "message": message
                        }
                    }
                }
            )
            logger.info(f"✅ Created next best action result: {result}")

        elif signal == "search-friction":
            logger.info("🔍 Processing search-friction signal...")
            intent = await mcp.call_tool(
                "get_session_intent",
                {"uid": uid, "sid": sid}
            )
            logger.info(f"🔍 Retrieved session intent: {intent}")

            prompt = f"Based on this intent data, what is the user looking for?\n{intent}"
            query = ask_llm(prompt)
            logger.info(f"Generated search query: {query}")

            products = await mcp.call_tool(
                "vector_search_products",
                {"query": query}
            )
            logger.info(f"📦 Found {len(products) if products else 0} products")

            if products:
                p = products[0]
                logger.info(f"Recommending product: {p.get('name', 'Unknown')}")
                result = await mcp.call_tool(
                    "create_next_best_action",
                    {
                        "action": {
                            "uid": uid,
                            "sid": sid,
                            "type": "product-recommendation",
                            "actionMetadata": {
                                "title": "Still deciding?",
                                "message": f"You might like {p['name']}",
                                "product": p
                            }
                        }
                    }
                )
                logger.info(f"✅ Created product recommendation result: {result}")
            else:
                logger.warning("No products found for recommendation")

        elif signal == "exit-risk":
            logger.info("🚨 Processing exit-risk signal...")

            severity = doc.get("severity", "low")
            discount_response = await mcp.call_tool(
                "discount_message",
                {"severity": severity}
            )
            
            logger.info(f"🔍 DEBUG: discount_response type: {type(discount_response)}, value: {discount_response}")
            
            # Handle if MCP wraps the response in a list with TextContent
            if isinstance(discount_response, list) and len(discount_response) > 0:
                first_item = discount_response[0]
                logger.info(f"🔍 DEBUG: Extracted from list, discount type: {type(first_item)}, value: {first_item}")
                
                # Check if it's a TextContent object and parse the JSON
                if hasattr(first_item, 'text'):
                    import json
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
            
            logger.info(f"💰 Created discount - Title: {discount['title']}, Message: {discount['message']}")
            
            result = await mcp.call_tool(
                "create_next_best_action",
                {
                    "action": {
                        "uid": uid,
                        "sid": sid,
                        "type": "delivery-discount",
                        "actionMetadata": {
                            "title": discount["title"],
                            "message": discount["message"]
                        }
                    }
                }
            )
            logger.info(f"✅ Created exit-risk action result: {result}")
        
        else:
            logger.warning(f"Unknown signal type: {signal}")
            
        logger.info(f"✅ Completed processing signal: {signal}")
        
    except Exception as e:
        logger.error(f"Error processing signal: {str(e)}", exc_info=True)
        raise
