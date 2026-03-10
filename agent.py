import logging
from typing import Dict, Any
from handlers import SocialProofHandler, ProductDiscountAndRecommendationHandler, ShippingDiscountHandler

logger = logging.getLogger(__name__)

# Strategy Pattern: Signal type to handler mapping
SIGNAL_HANDLERS = {
    "high-intent": SocialProofHandler(),
    "search-friction": ProductDiscountAndRecommendationHandler(),
    "exit-risk": ShippingDiscountHandler()
}

async def handle_signal(doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main signal processing dispatcher using Strategy Pattern
    
    Routes signals to appropriate NBA handlers based on signal type
    """
    logger.info(f"🔄 Processing signal from document: {doc.get('_id', 'unknown')}")
    
    try:
        signal = doc.get("signal")
        
        if not signal:
            logger.warning("Document missing 'signal' field")
            return {"status": "error", "message": "Missing signal field"}
        
        logger.info(f"Signal type: {signal}")
        
        # Get appropriate handler for signal type
        handler = SIGNAL_HANDLERS.get(signal)
        
        if not handler:
            logger.warning(f"Unknown signal type: {signal}")
            return {"status": "error", "message": f"Unknown signal type: {signal}"}
        
        # Process signal using appropriate handler
        result = await handler.process(doc)
        
        logger.info(f"✅ Completed processing signal: {signal}")
        return {"status": "success", "result": result}
        
    except Exception as e:
        logger.error(f"Error processing signal: {str(e)}", exc_info=True)
        return {"status": "error", "message": str(e)}
