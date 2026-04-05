import os
import requests
from config import VOYAGE_EMBEDDING_MODEL

# MongoDB Atlas AI endpoint configuration
_api_key = os.environ.get("VOYAGE_API_KEY")
_api_url = os.environ.get("VOYAGE_API_URL", "https://ai.mongodb.com/v1/embeddings")

if not _api_key:
    raise RuntimeError(
        "VOYAGE_API_KEY environment variable is not set. "
        "Set VOYAGE_API_KEY to your MongoDB Atlas API key before using embeddings."
    )

def get_embedding(text: str, input_type: str = "document") -> list:
    """Generate embeddings using MongoDB Atlas AI endpoint"""
    response = requests.post(
        _api_url,
        json={
            "model": VOYAGE_EMBEDDING_MODEL,
            "input": text,
        },
        headers={
            "Authorization": f"Bearer {_api_key}",
            "Content-Type": "application/json",
        },
        timeout=10,
    )
    response.raise_for_status()
    data = response.json()
    return data["data"][0]["embedding"]
