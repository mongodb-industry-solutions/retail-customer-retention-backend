from mcp_server.server import mcp  # Import the single mcp instance shared across your project  
from mongo import get_db
from config import PRODUCTS_COLLECTION, VECTOR_INDEX_NAME

@mcp.tool(
    name="vector_search_products",
    description="Vector search for products using intent text"
)
def vector_search_products(query: str, limit: int = 3) -> list:
    db = get_db()

    pipeline = [
        {
            "$search": {
                "index": VECTOR_INDEX_NAME,
                "text": {
                    "query": query,
                    "path": "vai_text_embedding"
                }
            }
        },
        {"$limit": limit},
        {
            "$project": {
                "name": 1,
                "imageUrl": 1
            }
        }
    ]

    return list(db[PRODUCTS_COLLECTION].aggregate(pipeline))
