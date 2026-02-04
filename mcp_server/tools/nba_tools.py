from mcp_server.server import mcp  # Import the single mcp instance shared across your project  
from mongo import get_db
from config import NEXT_BEST_ACTION_COLLECTION
from datetime import datetime

@mcp.tool(
    name="create_next_best_action",
    description="Persist a Next Best Action"
)
def create_next_best_action(action: dict) -> dict:
    db = get_db()
    action["ts"] = datetime.utcnow()
    action["redeemed"] = False

    db[NEXT_BEST_ACTION_COLLECTION].insert_one(action)
    return {"status": "ok"}
