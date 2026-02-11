from mcp_server.server import mcp  # Import the single mcp instance shared across your project  
from mongo import get_db
from config import SESSION_STATE_COLLECTION, SESSION_SIGNALS_COLLECTION
import logging

@mcp.tool(
    name="get_session_search_history",
    description="Fetch search history (array of search query strings) for a session"
)
def get_session_search_history(uid: str, sid: str) -> list:
    logging.info("🔍 Fetching session search history...")
    
    db = get_db()

    query = {"userId": uid, "sessionId": sid}
    projection = {"_id": 1, "searchHistory": 1}
    
    logging.info("📊 Executing MongoDB query for session search history")
    
    doc = db[SESSION_STATE_COLLECTION].find_one(query, projection)

    if doc is None:
        logging.warning("⚠️ No session document found for requested session")
        return []
    
    doc_id = doc.get("_id")
    logging.info(f"📄 Found session document with _id: {doc_id}")
    
    search_history = doc.get("searchHistory", [])
    logging.info(f"✅ Retrieved search history: {len(search_history) if isinstance(search_history, list) else 0} queries")
    
    # Ensure we return a list
    if isinstance(search_history, list):
        return search_history
    else:
        logging.info(f"⚠️ searchHistory is not a list, got {type(search_history)}, returning empty list")
        return []

@mcp.tool(
    name="get_session_signals",
    description="Fetch past behavioral signals for a session"
)
def get_session_signals(uid: str, sid: str) -> list:
    logging.info("🔍 Fetching session signals")
    
    db = get_db()
    
    query = {"uid": uid, "sid": sid, "signal": "search-friction"}
    
    logging.info(f"📊 Executing MongoDB query: {query}")
    
    # Get all signals for this session, sorted by timestamp (most recent first)
    signals_cursor = db[SESSION_SIGNALS_COLLECTION].find(query).sort("ts", -1)
    
    # Also check total count to debug
    total_count = db[SESSION_SIGNALS_COLLECTION].count_documents(query)
    logging.info(f"📊 Total documents matching query: {total_count}")
    
    signals = []
    
    for doc in signals_cursor:
        # Convert MongoDB document to JSON-serializable dict
        json_doc = {}
        for key, value in doc.items():
            if key == '_id':
                json_doc[key] = str(value)  # Convert ObjectId to string
            elif hasattr(value, 'isoformat'):  # Handle datetime objects
                json_doc[key] = value.isoformat()
            elif isinstance(value, (dict, list, str, int, float, bool)) or value is None:
                json_doc[key] = value  # Already JSON-serializable
            else:
                json_doc[key] = str(value)  # Convert other types to string
        signals.append(json_doc)
    
    logging.info(f"🔍 Final signals list length: {len(signals)}")
    
    # Test JSON serializability to ensure MCP can handle the data
    try:
        import json
        json_test = json.dumps(signals)
        logging.info(f"✅ JSON serialization test passed - {len(json_test)} chars")
    except Exception as e:
        logging.error(f"❌ JSON serialization test failed: {e}")
        # If serialization fails, return empty list to avoid MCP issues
        return []
    
    logging.info(f"📤 Returning {len(signals)} signals from get_session_signals")
    return signals