import os

# Mongo
MONGODB_URI = os.environ["MONGODB_URI"]
DB_NAME = "leafy_popup_store"

CUSTOMER_BEHAVIOR_COLLECTION = "session_signals"
SESSION_STATE_COLLECTION = "session_state"
PRODUCTS_COLLECTION = "products"
NEXT_BEST_ACTION_COLLECTION = "next_best_actions"

# Vector search
VECTOR_INDEX_NAME = "vs_index_vai_text_embeddings"
EMBEDDING_FIELD = "vai_text_embedding"

# AWS
AWS_REGION = "us-east-1"
BEDROCK_MODEL_ID = "anthropic.claude-3-haiku-20240307-v1:0"
