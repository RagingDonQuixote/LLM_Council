"""OpenRouter API client for making LLM requests."""

import httpx
from typing import List, Dict, Any, Optional
from .config import OPENROUTER_API_KEY, OPENROUTER_API_URL


async def query_model(
    model: str,
    messages: List[Dict[str, str]],
    timeout: float = 120.0
) -> Optional[Dict[str, Any]]:
    """
    Query a single model via OpenRouter API.

    Args:
        model: OpenRouter model identifier (e.g., "openai/gpt-4o")
        messages: List of message dicts with 'role' and 'content'
        timeout: Request timeout in seconds

    Returns:
        Response dict with 'content' and optional 'reasoning_details', or None if failed
    """
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "messages": messages,
    }

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                OPENROUTER_API_URL,
                headers=headers,
                json=payload
            )
            response.raise_for_status()

            data = response.json()
            message = data['choices'][0]['message']
            usage = data.get('usage', {})

            return {
                'content': message.get('content'),
                'reasoning_details': message.get('reasoning_details'),
                'usage': {
                    'prompt_tokens': usage.get('prompt_tokens', 0),
                    'completion_tokens': usage.get('completion_tokens', 0),
                    'total_tokens': usage.get('total_tokens', 0)
                }
            }

    except Exception as e:
        print(f"Error querying model {model}: {e}")
        return None


async def query_models_parallel(
    models: List[str],
    messages: List[Dict[str, str]]
) -> Dict[str, Optional[Dict[str, Any]]]:
    """
    Query multiple models in parallel.

    Args:
        models: List of OpenRouter model identifiers
        messages: List of message dicts to send to each model

    Returns:
        Dict mapping model identifier to response dict (or None if failed)
    """
    import asyncio

    # Create tasks for all models
    tasks = [query_model(model, messages) for model in models]

    # Wait for all to complete
    responses = await asyncio.gather(*tasks)

    # Map models to their responses
    return {model: response for model, response in zip(models, responses)}


async def get_available_models() -> List[Dict[str, Any]]:
    """
    Fetch available models from OpenRouter API with pricing information.

    Returns:
        List of model dicts with id, name, free status, and pricing
    """
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                "https://openrouter.ai/api/v1/models",
                headers=headers
            )
            response.raise_for_status()

            data = response.json()
            models = []

            for model in data.get('data', []):
                model_id = model.get('id', '')
                name = model.get('name', model_id)

                # Extract pricing - OpenRouter returns pricing per token
                pricing = model.get('pricing', {})
                prompt_price = pricing.get('prompt')
                completion_price = pricing.get('completion')

                # Ensure prices are numeric (handle None, str cases)
                try:
                    prompt_price = float(prompt_price) if prompt_price is not None else 0
                except (ValueError, TypeError):
                    prompt_price = 0

                try:
                    completion_price = float(completion_price) if completion_price is not None else 0
                except (ValueError, TypeError):
                    completion_price = 0

                # Determine if free - only true if both prices are exactly 0 (not negative)
                is_free = prompt_price == 0 and completion_price == 0

                # Format cost display
                if is_free:
                    cost_display = "(FREE)"
                else:
                    # Show prompt price per million tokens, formatted nicely
                    if prompt_price > 0:
                        # Convert from per-token to per-million tokens
                        cost_per_million = prompt_price * 1000000
                        if cost_per_million >= 0.01:
                            cost_str = f"${cost_per_million:.2f}"
                        elif cost_per_million >= 0.001:
                            cost_str = f"${cost_per_million:.3f}"
                        elif cost_per_million >= 0.0001:
                            cost_str = f"${cost_per_million:.4f}"
                        else:
                            # For very small amounts, show more precision but remove trailing zeros
                            cost_str = f"${cost_per_million:.6f}".rstrip('0').rstrip('.')
                        cost_display = f"({cost_str}/mT)"
                    elif prompt_price < 0:
                        # Handle negative prices (likely errors or special cases)
                        cost_display = "(ERROR)"
                    else:
                        cost_display = "(FREE)"

                models.append({
                    'id': model_id,
                    'name': f"{name} {cost_display}",
                    'free': is_free,
                    'pricing': {
                        'prompt': prompt_price,
                        'completion': completion_price
                    }
                })

            return models

    except Exception as e:
        print(f"Error fetching models from OpenRouter: {e}")
        return []
