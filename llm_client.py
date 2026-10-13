from langchain_anthropic import ChatAnthropic

from config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL

_client = ChatAnthropic(
    model=LLM_MODEL,
    api_key=LLM_API_KEY,
    base_url=LLM_BASE_URL,
    max_tokens=300,
)


def ask_llm(prompt: str) -> str:
    response = _client.invoke(prompt)
    if isinstance(response.content, str):
        return response.content
    return "".join(
        block if isinstance(block, str) else block.get("text", "")
        for block in response.content
        if isinstance(block, str) or block.get("type") == "text"
    )