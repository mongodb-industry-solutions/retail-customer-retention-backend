from bedrock import ask_llm
from mcp_server.server import mcp

def handle_signal(doc: dict):
    signal = doc["signal"]

    if signal == "high-intent":
        message = ask_llm(
            f"Write a short social proof message based on: {doc['evidence']}"
        )

        mcp.call_tool(
            "create_next_best_action",
            {
                "uid": doc["uid"],
                "sid": doc["sid"],
                "type": "social-proof-notification",
                "actionMetadata": {
                    "title": "Popular pick!",
                    "message": message
                }
            }
        )

    elif signal == "search-friction":
        intent = mcp.call_tool(
            "get_session_intent",
            {"uid": doc["uid"], "sid": doc["sid"]}
        )

        prompt = f"Based on this intent data, what is the user looking for?\n{intent}"
        query = ask_llm(prompt)

        products = mcp.call_tool(
            "vector_search_products",
            {"query": query}
        )

        if products:
            p = products[0]
            mcp.call_tool(
                "create_next_best_action",
                {
                    "uid": doc["uid"],
                    "sid": doc["sid"],
                    "type": "product-recommendation",
                    "actionMetadata": {
                        "title": "Still deciding?",
                        "message": f"You might like {p['name']}",
                        "product": p
                    }
                }
            )

    elif signal == "exit-risk":
        mcp.call_tool(
            "create_next_best_action",
            {
                "uid": doc["uid"],
                "sid": doc["sid"],
                "type": "free-delivery",
                "actionMetadata": {
                    "title": "Wait! Free Delivery Awaits",
                    "message": "Complete your purchase now and enjoy free delivery."
                }
            }
        )
