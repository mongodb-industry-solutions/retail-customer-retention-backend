import os

# Mongo
MONGODB_URI = os.environ["MONGODB_URI"]
DB_NAME = "leafy_popup_store"

SESSION_SIGNALS_COLLECTION = "session_signals"
SESSION_STATE_COLLECTION = "session_state"
PRODUCTS_COLLECTION = "products"
NEXT_BEST_ACTION_COLLECTION = "next_best_actions"

# Vector search
VECTOR_INDEX_NAME = "vs_index_vai_text_embeddings"
SEARCH_INDEX_NAME = "search_index_products"
EMBEDDING_FIELD = "vai_text_embedding"

# VoyageAI
VOYAGE_EMBEDDING_MODEL = "voyage-3-large"

# LLM
LLM_API_KEY = os.environ["LLM_API_KEY"]
LLM_BASE_URL = os.environ["LLM_BASE_URL"]
LLM_MODEL = os.environ["LLM_MODEL"]
