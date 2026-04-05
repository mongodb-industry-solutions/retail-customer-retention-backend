import logging
import asyncio
from dotenv import load_dotenv
load_dotenv()
from threading import Thread
from fastapi import FastAPI
import uvicorn
from mcp_server.server import mcp
from change_stream import watch_customer_behavior

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app for HTTP endpoints (required by Kanopy)
app = FastAPI(title="Retail Customer Retention Backend")

@app.get("/")
def health_check():
    """Health check endpoint for Kanopy container liveness"""
    return {"status": "healthy", "service": "retail-customer-retention-backend"}

@app.get("/health")
def health():
    """Additional health endpoint"""
    return {"status": "ok"}

if __name__ == "__main__":
    logger.info("Starting retail customer retention backend...")
    
    import os
    try:
        # Start the change stream watcher in a separate thread
        logger.info("Starting change stream watcher thread...")
        change_stream_thread = Thread(target=watch_customer_behavior, daemon=True)
        change_stream_thread.start()
        logger.info("Change stream thread started successfully")
        
        # Start the FastAPI server (includes HTTP endpoints for Kanopy)
        port = int(os.environ.get("PORT", 8081))
        logger.info(f"Starting FastAPI server on port {port}...")
        uvicorn.run(app, host="0.0.0.0", port=port)
        
    except Exception as e:
        logger.error(f"Failed to start application: {str(e)}", exc_info=True)
        raise
