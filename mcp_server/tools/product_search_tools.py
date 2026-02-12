from mcp_server.server import mcp  # Import the single mcp instance shared across your project  
from mongo import get_db
from config import PRODUCTS_COLLECTION, SEARCH_INDEX_NAME, VECTOR_INDEX_NAME, EMBEDDING_FIELD
from voyageai_client import get_embedding  # For vector search
from bson import ObjectId

# Common projection for all search types
PRODUCT_PROJECTION = {
    "name": 1,
    "image.url": 1,
    "masterCategory": 1,
    "articleType": 1,
    "subCategory": 1,
    "brand": 1
}

@mcp.tool(
    name="vector_search_products",
    description="Vector search for products using intent text - best for semantic similarity"
)
def vector_search_products(query: str, limit: int = 3) -> list:
    """Semantic vector search using embeddings"""
    db = get_db()
    
    # First, embed the query text
    query_vector = get_embedding(query)

    pipeline = [
        {
            "$vectorSearch": {
                "index": VECTOR_INDEX_NAME,
                "path": EMBEDDING_FIELD,
                "queryVector": query_vector,
                "numCandidates": 100,
                "limit": limit
            }
        },
        {
            "$project": {
                **PRODUCT_PROJECTION,
                "score": {"$meta": "vectorSearchScore"}
            }
        }
    ]

    return list(db[PRODUCTS_COLLECTION].aggregate(pipeline))

@mcp.tool(
    name="search_product_by_id",
    description="Search for a specific product by its MongoDB ObjectId"
)
def search_product_by_id(product_id: str) -> dict:
    """Search for a product by its _id field"""
    db = get_db()
    
    try:
        # Convert string ID to ObjectId
        object_id = ObjectId(product_id)
        
        # Find the product by _id
        result = db[PRODUCTS_COLLECTION].find_one(
            {"_id": object_id},
            PRODUCT_PROJECTION
        )
        
        if result:
            return result
        else:
            return {"error": f"No product found with ID: {product_id}"}
            
    except Exception as e:
        return {"error": f"Invalid ObjectId format or database error: {str(e)}"}