import voyageai
import os
from config import VOYAGE_EMBEDDING_MODEL

# Initialize VoyageAI client
_api_key = os.environ.get("VOYAGE_API_KEY")
if not _api_key:
    raise RuntimeError(
        "VOYAGE_API_KEY environment variable is not set. "
        "Set VOYAGE_API_KEY to your VoyageAI API key before using embeddings."
    )
_client = voyageai.Client(api_key=_api_key)

def get_embedding(text: str, input_type: str = "document") -> list:
    """Generate embeddings using VoyageAI"""
    result = _client.embed([text], model=VOYAGE_EMBEDDING_MODEL, input_type=input_type)
    return result.embeddings[0]