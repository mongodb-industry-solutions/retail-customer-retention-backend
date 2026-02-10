from mcp_server.server import mcp  # Import the single mcp instance shared across your project  
from mongo import get_db
from config import SESSION_STATE_COLLECTION, CUSTOMER_BEHAVIOR_COLLECTION
import logging

@mcp.tool(
    name="get_session_intent",
    description="Fetch search history (array of search query strings) for a session"
)
def get_session_intent(uid: str, sid: str) -> list:
    logging.info("🔍 Fetching session search history")
    
    db = get_db()

    query = {"userId": uid, "sessionId": sid}
    projection = {"_id": 1, "searchHistory": 1}
    
    logging.debug("📊 Executing MongoDB query for session search history")
    
    doc = db[SESSION_STATE_COLLECTION].find_one(query, projection)

    if doc is None:
        logging.warning("⚠️ No session document found for requested session")
        return []
    
    doc_id = doc.get("_id")
    logging.debug(f"📄 Found session document with _id: {doc_id}")
    
    search_history = doc.get("searchHistory", [])
    logging.debug(f"✅ Retrieved search history: {len(search_history) if isinstance(search_history, list) else 0} queries")
    
    # Ensure we return a list
    if isinstance(search_history, list):
        return search_history
    else:
        logging.warning(f"⚠️ searchHistory is not a list, got {type(search_history)}, returning empty list")
        return []

@mcp.tool(
    name="get_session_signals",
    description="Fetch past behavioral signals for a session"
)
def get_session_signals(uid: str, sid: str) -> list:
    logging.info("🔍 Fetching session signals")
    
    db = get_db()
    
    query = {"uid": uid, "sid": sid}
    projection = {"_id": 1, "signal": 1, "evidence": 1, "severity": 1, "ts": 1}
    
    logging.debug("📊 Executing MongoDB query for session signals")
    
    # Get all signals for this session, sorted by timestamp (most recent first)
    signals = list(db[CUSTOMER_BEHAVIOR_COLLECTION].find(query, projection).sort("ts", -1))
    
    logging.debug(f"📄 Found {len(signals)} signals for session")
    
    return signals