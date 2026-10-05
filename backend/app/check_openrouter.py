"""Explicit live smoke check: docker compose exec -T app python -m app.check_openrouter."""

import asyncio

from app.openrouter import MODEL, OpenRouterError, complete


async def check() -> None:
    answer = await complete([{"role": "user", "content": "What is 2+2? Reply with only the digit 4."}])
    if answer != "4":
        raise OpenRouterError("unexpected_answer", "Connectivity check did not return the expected answer.")
    print(f"OpenRouter connectivity passed: {MODEL}; 2+2 = 4")


def main() -> None:
    try:
        asyncio.run(check())
    except OpenRouterError as error:
        raise SystemExit(f"OpenRouter check failed ({error.code}): {error}") from None


if __name__ == "__main__":
    main()
