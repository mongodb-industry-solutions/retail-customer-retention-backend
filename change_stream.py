import logging
import asyncio
from mongo import get_db
from config import CUSTOMER_BEHAVIOR_COLLECTION
from agent import handle_signal

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def watch_customer_behavior():
    logger.info("🚀 Starting customer behavior change stream watcher...")
    
    try:
        db = get_db()
        logger.info(f"✅ Successfully connected to database: {db.name}")
        
        collection = db[CUSTOMER_BEHAVIOR_COLLECTION]
        logger.info(f"🔍 Watching collection: {CUSTOMER_BEHAVIOR_COLLECTION}")
        
        # Check if collection exists and has documents
        doc_count = collection.count_documents({})
        logger.info(f"📊 Collection has {doc_count} documents")
        
        pipeline = [{"$match": {"operationType": "insert"}}]
        logger.info(f"⚙️ Using pipeline: {pipeline}")
        
        with collection.watch(pipeline) as stream:
            logger.info("🎧 Change stream successfully opened, waiting for changes...")
            
            for change in stream:
                try:
                    logger.info(f"🔄 Detected change: {change.get('operationType', 'unknown')} operation")
                    logger.debug(f"📋 Full change document: {change}")
                    
                    if "fullDocument" in change:
                        document = change["fullDocument"]
                        logger.info(f"📄 Processing document with _id: {document.get('_id', 'unknown')}")
                        logger.debug(f"💾 Document content: {document}")
                        
                        # Call the signal handler
                        try:
                            loop = asyncio.get_event_loop()
                            if loop.is_running():
                                # If there's already an event loop running, create a task
                                asyncio.create_task(handle_signal(document))
                            else:
                                # If no event loop is running, run it
                                asyncio.run(handle_signal(document))
                        except RuntimeError:
                            # No event loop exists, create and run one
                            asyncio.run(handle_signal(document))
                        logger.info("✅ Successfully processed document through signal handler")
                        
                    else:
                        logger.warning("⚠️ Change document missing 'fullDocument' field")
                        
                except Exception as e:
                    logger.error(f"❌ Error processing change document: {str(e)}", exc_info=True)
                    # Continue processing other changes even if one fails
                    continue
                    
    except Exception as e:
        logger.error(f"💥 Fatal error in change stream watcher: {str(e)}", exc_info=True)
        raise
