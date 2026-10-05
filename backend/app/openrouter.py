"""Backend-only OpenRouter chat completion client; no automatic retries."""

import asyncio
import os

import httpx2 as httpx

MODEL = "openai/gpt-oss-120b"
URL = "https://openrouter.ai/api/v1/chat/completions"
TIMEOUT_SECONDS = 60


class OpenRouterError(Exception):
    """Safe application error, without provider bodies, prompts, or credentials."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def provider_error(status: int) -> OpenRouterError:
    code, message = {
        401: ("authentication", "OpenRouter rejected the API key. Check backend configuration."),
        402: ("credits", "OpenRouter credits are insufficient."),
        403: ("forbidden", "OpenRouter denied this request."),
        408: ("timeout", "OpenRouter timed out. Please try again."),
        429: ("rate_limit", "OpenRouter rate limit reached. Please try again later."),
        504: ("timeout", "OpenRouter timed out. Please try again."),
    }.get(status, ("provider", "OpenRouter could not complete the request. Please try again."))
    return OpenRouterError(code, message)


async def complete(messages: list[dict[str, str]], *, response_format: dict | None = None) -> str:
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not key:
        raise OpenRouterError("configuration", "OPENROUTER_API_KEY is not configured on the backend.")

    payload = {
        "model": MODEL,
        "messages": messages,
        "stream": False,
        "max_tokens": 2048,
        "reasoning": {"effort": "low", "exclude": True},
        "provider": {"require_parameters": True},
    }
    if response_format is not None:
        payload["response_format"] = response_format
    try:
        # Bound the whole request as well as individual network operations.
        async with asyncio.timeout(TIMEOUT_SECONDS):
            async with httpx.AsyncClient(timeout=httpx.Timeout(TIMEOUT_SECONDS, connect=10)) as client:
                response = await client.post(URL, headers={"Authorization": f"Bearer {key}"}, json=payload)
    except (TimeoutError, httpx.TimeoutException):
        raise provider_error(408) from None
    except httpx.RequestError:
        raise OpenRouterError("network", "Unable to reach OpenRouter. Please try again.") from None

    if not response.is_success:
        raise provider_error(response.status_code)
    try:
        data = response.json()
    except ValueError:
        raise OpenRouterError("invalid_response", "OpenRouter returned an invalid response.") from None
    if isinstance(data, dict) and "error" in data:
        error = data["error"]
        status = error.get("code") if isinstance(error, dict) else None
        raise provider_error(status if isinstance(status, int) else 502)
    try:
        choice = data["choices"][0]
        content = choice["message"]["content"]
        if choice["finish_reason"] != "stop" or not isinstance(content, str) or not content.strip():
            raise ValueError
    except (KeyError, IndexError, TypeError, ValueError):
        raise OpenRouterError("invalid_response", "OpenRouter returned an empty or incomplete response.") from None
    return content.strip()
