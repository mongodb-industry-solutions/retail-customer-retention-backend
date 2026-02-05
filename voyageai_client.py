import voyageai
import os
from config import VOYAGE_EMBEDDING_MODEL

# Initialize VoyageAI client
_client = voyageai.Client(api_key=os.environ.get("VOYAGE_API_KEY"))

def get_embedding(text: str, input_type: str = "document") -> list:
    """Generate embeddings using VoyageAI"""
    result = _client.embed([text], model=VOYAGE_EMBEDDING_MODEL, input_type=input_type)
    return result.embeddings[0]