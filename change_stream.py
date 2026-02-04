from mongo import get_db
from config import CUSTOMER_BEHAVIOR_COLLECTION
from agent import handle_signal

def watch_customer_behavior():
    db = get_db()
    collection = db[CUSTOMER_BEHAVIOR_COLLECTION]

    with collection.watch([{"$match": {"operationType": "insert"}}]) as stream:
        for change in stream:
            handle_signal(change["fullDocument"])
