from mcp_server.server import mcp  # Import the single mcp instance shared across your project  
from mongo import get_db
from config import SESSION_STATE_COLLECTION
import logging

@mcp.tool(
    name="get_session_intent",
    description="Fetch aggregated intent data for a session"
)
def get_session_intent(uid: str, sid: str) -> dict:
    logging.info(f"🔍 Fetching session intent for user {uid}, session {sid}")
    
    db = get_db()

    query = {"userId": uid, "sessionId": sid}
    projection = {"_id": 1, "last10s.intent": 1}
    
    logging.info(f"📊 Executing MongoDB query: {query} with projection: {projection}")
    
    doc = db[SESSION_STATE_COLLECTION].find_one(query, projection)

    if doc is None:
        logging.warning(f"⚠️ No session document found for user {uid}, session {sid}")
        return {}
    
    doc_id = doc.get("_id")
    logging.info(f"📄 Found session document with _id: {doc_id}")
    
    intent_data = doc.get("last10s", {}).get("intent", {})
    logging.info(f"✅ Retrieved intent data: {intent_data}")
    
    return intent_data