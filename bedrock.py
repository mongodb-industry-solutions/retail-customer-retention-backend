import boto3
import json
from config import AWS_REGION, BEDROCK_MODEL_ID

_client = boto3.client("bedrock-runtime", region_name=AWS_REGION)

def ask_llm(prompt: str) -> str:
    response = _client.invoke_model(
        modelId=BEDROCK_MODEL_ID,
        body=json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 300,
            "temperature": 0.4
        })
    )

    body = json.loads(response["body"].read())
    return body["content"][0]["text"]
