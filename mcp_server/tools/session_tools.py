from mcp_server.server import mcp  # Import the single mcp instance shared across your project  
from mongo import get_db
from config import SESSION_STATE_COLLECTION

@mcp.tool(
    name="get_session_intent",
    description="Fetch aggregated intent data for a session"
)
def get_session_intent(uid: str, sid: str) -> dict:
    db = get_db()

    doc = db[SESSION_STATE_COLLECTION].find_one(
        {"uid": uid, "sid": sid},
        {"sessionTotals.intent": 1}
    )

    return doc.get("sessionTotals", {}).get("intent", {})
