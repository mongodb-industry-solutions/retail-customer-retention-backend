from mcp_server.server import mcp  # Import the single mcp instance shared across your project  
from mongo import get_db
from config import SESSION_STATE_COLLECTION
import logging

@mcp.tool(
    name="get_session_intent",
    description="Fetch aggregated intent data for a session"
)
def get_session_intent(uid: str, sid: str) -> dict:
    logging.info("🔍 Fetching session intent")
    
    db = get_db()

    query = {"userId": uid, "sessionId": sid}
    projection = {"_id": 1, "last10s.intent": 1}
    
    logging.debug("📊 Executing MongoDB query for session intent with predefined projection")
    
    doc = db[SESSION_STATE_COLLECTION].find_one(query, projection)

    if doc is None:
        logging.warning("⚠️ No session document found for requested session")
        return {}
    
    doc_id = doc.get("_id")
    logging.debug(f"📄 Found session document with _id: {doc_id}")
    
    intent_data = doc.get("last10s", {}).get("intent", {})
    logging.debug("✅ Retrieved intent data for session")
    
    return intent_data