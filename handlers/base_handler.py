from abc import ABC, abstractmethod
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class BaseNBAHandler(ABC):
    """Base class for all NBA handlers"""
    
    @abstractmethod
    async def process(self, signal_doc: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a signal document and return the result
        
        Args:
            signal_doc: Signal document from MongoDB change stream
            
        Returns:
            Dict containing the processing result
        """
        pass
    
    def extract_signal_data(self, signal_doc: Dict[str, Any]) -> Dict[str, Any]:
        """Extract common signal data"""
        return {
            "uid": signal_doc.get("uid"),
            "sid": signal_doc.get("sid"), 
            "signal_id": signal_doc.get("_id"),
            "signal": signal_doc.get("signal"),
            "severity": signal_doc.get("severity", "low"),
            "evidence": signal_doc.get("evidence", "No evidence provided"),
            "product_id": signal_doc.get("productId")
        }
    
    def log_processing_start(self, signal_type: str, uid: str, sid: str):
        """Standard logging for processing start"""
        logger.info(f"🔄 Processing {signal_type} signal for user: {uid}, session: {sid}")
    
    def log_processing_complete(self, signal_type: str):
        """Standard logging for processing completion"""  
        logger.info(f"✅ Completed processing {signal_type} signal")