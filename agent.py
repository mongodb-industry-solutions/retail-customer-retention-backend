import logging
import json
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
        id = doc.get("_id")
        logger.info(f"👤 Processing for user: {uid}, session: {sid}")

        if signal == "high-intent":
            logger.info("🎯 Processing high-intent signal... To generate a Social proof notification")
            evidence = doc.get('evidence', 'No evidence provided')
            severity = doc.get("severity", "low")
            logger.debug(f"Evidence: {evidence}")
            
            notification_raw = ask_llm(
                f"""
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
            )
            logger.info(f"Generated raw response: {notification_raw}")
            
            # Parse and validate LLM response
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
                
            except (json.JSONDecodeError, ValueError, KeyError) as e:
                logger.error(f"❌ Failed to parse LLM response: {e}. Using fallback.")
                # Fallback notification
                notification = {
                    "title": "Popular Choice!",
                    "message": f"A few shoppers made a purchase in the last 24 hours."
                }
                logger.info(f"🔄 Using fallback notification: {notification}")

            result = await mcp.call_tool(
                "create_next_best_action",
                {
                    "action": {
                        "uid": uid,
                        "sid": sid,
                        "signalId": id,
                        "type": "social-proof-notification",
                        "actionMetadata": {
                            "title": notification["title"],
                            "message": notification["message"]
                        }
                    }
                }
            )
            logger.info(f"✅ Created next best action result: {result}")

        elif signal == "search-friction":
            logger.info("🔍 Processing search-friction signal... To generate a product recommendation")
            
            try:
                logger.info(f"📞 Calling get_session_intent with uid: {uid}, sid: {sid}")
                intent = await mcp.call_tool(
                    "get_session_intent",
                    {"uid": uid, "sid": sid}
                )
                logger.info(f"🔍 Retrieved session intent type: {type(intent)}, value: {intent}")
                
                # Handle potential MCP wrapper response
                if isinstance(intent, list) and len(intent) > 0:
                    first_item = intent[0]
                    if hasattr(first_item, 'text'):
                        try:
                            intent = json.loads(first_item.text)
                            logger.info(f"🔍 Parsed intent from TextContent: {intent}")
                        except json.JSONDecodeError:
                            intent = {}
                            logger.warning("⚠️ Failed to parse intent JSON, using empty dict")
                    else:
                        intent = first_item
                
                # Ensure intent is a dict
                if not isinstance(intent, dict):
                    logger.warning(f"⚠️ Intent is not a dict, got {type(intent)}, using empty dict")
                    intent = {}
                    
            except Exception as e:
                logger.error(f"❌ Error calling get_session_intent: {e}")
                intent = {}
                
            logger.info(f"🔍 Final processed intent: {intent}")

            if intent:
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
            else:
                logger.warning("⚠️ No intent data available, skipping product recommendation")

        elif signal == "exit-risk":
            logger.info("🚨 Processing exit-risk signal... to generate a delivery discount")

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
                        "signalId": id,
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
