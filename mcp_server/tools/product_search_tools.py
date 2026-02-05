from mcp_server.server import mcp  # Import the single mcp instance shared across your project  
from mongo import get_db
from config import PRODUCTS_COLLECTION, SEARCH_INDEX_NAME, VECTOR_INDEX_NAME, EMBEDDING_FIELD
from voyageai_client import get_embedding  # For vector search

# Common projection for all search types
PRODUCT_PROJECTION = {
    "name": 1,
    "imageUrl": 1,
    "description": 1,
    "category": 1,
    "price": 1,
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
    name="text_search_products",
    description="Text search for products using product names and descriptions - best for exact matches"
)
def text_search_products(query: str, limit: int = 3) -> list:
    db = get_db()

    pipeline = [
        {
            "$search": {
                "index": SEARCH_INDEX_NAME,
                "text": {
                    "query": query,
                    "path": ["name", "articleType", "subCategory", "brand"]
                }
            }
        },
        {"$limit": limit},
        {
            "$project": {
                **PRODUCT_PROJECTION,
                "score": {"$meta": "searchScore"}
            }
        }
    ]

    return list(db[PRODUCTS_COLLECTION].aggregate(pipeline))

@mcp.tool(
    name="search_products_by_sub_category",
    description="Search products by sub-category with optional text filtering"
)
def search_products_by_sub_category(sub_category: str, text_filter: str = None, limit: int = 3) -> list:
    db = get_db()

    match_stage = {}  
    
    # Match subCategory using $eq (exact match)  
    if sub_category:  
        match_stage["subCategory"] = sub_category  # Exact match (case-sensitive unless normalized in the DB)  

    # Use full-text search for text_filter  
    if text_filter:  
        match_stage["$text"] = {"$search": text_filter} 
    
    pipeline = [
        {"$match": match_stage},
        {"$limit": limit},
        {
            "$project": PRODUCT_PROJECTION
        }
    ]

    return list(db[PRODUCTS_COLLECTION].aggregate(pipeline))