import logging
from dotenv import load_dotenv
load_dotenv()
from threading import Thread
from mcp_server.server import mcp
from change_stream import watch_customer_behavior

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("Starting retail customer retention backend...")
    
    try:
        # Start the change stream watcher in a separate thread
        logger.info("Starting change stream watcher thread...")
        change_stream_thread = Thread(target=watch_customer_behavior, daemon=True)
        change_stream_thread.start()
        logger.info("Change stream thread started successfully")
        
        # Start the MCP server
        logger.info("Starting MCP server...")
        mcp.run()
        
    except Exception as e:
        logger.error(f"Failed to start application: {str(e)}", exc_info=True)
        raise
