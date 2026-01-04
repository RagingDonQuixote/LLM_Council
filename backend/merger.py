import json
import re

def normalize_provider_name(name: str) -> str:
    """Normalize provider name to be URL-safe (replace spaces/slashes with underscores)."""
    if not name:
        return "Unknown"
    return name.replace(" ", "_").replace("/", "_").replace("-", "_")

def merge_endpoint_strategy(base_json: dict, endpoint_json: dict) -> dict:
    """
    Merge logic for OpenRouter models.
    Source of Truth: Endpoint Data > Base Model Data.
    
    Returns a dictionary with all fields needed for UnifiedModel.
    """
    
    # --- 1. Identity & IDs ---
    base_id = base_json.get("id", "unknown")
    
    # Endpoint often doesn't have ID, so we rely on base_id but check endpoint for provider
    provider_name = endpoint_json.get("provider_name", "OpenRouter")
    provider_safe = normalize_provider_name(provider_name)
    
    # New unique ID: {base_id}:{provider_safe}
    # Example: openai/gpt-oss-120b:DeepInfra
    unique_id = f"{base_id}:{provider_safe}"
    
    # --- 2. Capabilities (Critical Override) ---
    # Logic: If endpoint has 'supported_parameters', use ONLY that.
    # If endpoint lacks it, fallback to base (but warn/flag it internally?)
    
    endpoint_params = endpoint_json.get("supported_parameters")
    base_params = base_json.get("supported_parameters", [])
    
    final_params = endpoint_params if endpoint_params is not None else base_params
    if final_params is None:
        final_params = []
        
    capabilities = {
        "function_calling": "tools" in final_params or "tool_choice" in final_params,
        "json_mode": "response_format" in final_params or "structured_outputs" in final_params,
        "reasoning": "reasoning" in final_params or "include_reasoning" in final_params,
        "vision": "image" in base_json.get("architecture", {}).get("input_modalities", []) # Vision is usually architectural, rarely removed by provider? Check pricing 'image' too.
    }
    
    # Double check vision via pricing
    ep_pricing = endpoint_json.get("pricing", {})
    if str(ep_pricing.get("image", "0")) != "0":
        capabilities["vision"] = True

    # --- 3. Pricing (Strict Override) ---
    # Endpoint pricing is the truth.
    base_pricing = base_json.get("pricing", {})
    final_pricing_obj = ep_pricing if ep_pricing else base_pricing
    
    prompt_price = float(final_pricing_obj.get("prompt", 0))
    completion_price = float(final_pricing_obj.get("completion", 0))
    
    cost_structure = {
        "cost_1mT_input_USD": prompt_price * 1_000_000,
        "cost_1mT_output_USD": completion_price * 1_000_000,
        "cost_currency": "USD",
        "cost_unit": "per_million_tokens",
        "is_free": (prompt_price == 0 and completion_price == 0)
    }

    # --- 4. Context Length (Strict Override) ---
    base_context = base_json.get("context_length", 0)
    endpoint_context = endpoint_json.get("context_length")
    
    # Use endpoint context if available, else base
    final_context = endpoint_context if endpoint_context is not None else base_context

    # --- 5. Technical Details ---
    quantization = endpoint_json.get("quantization", "unknown")
    
    technical = {
        "context_tokens": final_context,
        "max_output_tokens": endpoint_json.get("max_completion_tokens") or base_json.get("top_provider", {}).get("max_completion_tokens"),
        "quantization": quantization,
        "modality": base_json.get("architecture", {}).get("modality", "unknown")
    }

    # --- 6. Naming & Display ---
    # Developer
    if "/" in base_id:
        developer = base_id.split("/")[0]
        model_name = base_id.split("/", 1)[1]
    else:
        developer = "Unknown"
        model_name = base_id

    # Clean model name (remove 'openai/' if repeated etc, but we handled that with split)
    
    # Print Name Construction
    # Part 1: "OpenAI:gpt-4o"
    print_name_part1 = f"{developer}:{model_name}"
    
    # Part 2: "OR [Provider] [Quant] [Flags] [Price]"
    # Flags: R (Reasoning), V (Vision), T (Tools), J (JSON)
    flags = []
    if capabilities["reasoning"]: flags.append("R")
    if capabilities["vision"]: flags.append("V")
    if capabilities["function_calling"]: flags.append("T")
    if capabilities["json_mode"]: flags.append("J")
    flags_str = "".join(flags)
    
    provider_short = provider_name[:2].upper() if len(provider_name) >= 2 else provider_name.upper()
    
    # Price display
    if cost_structure["is_free"]:
        price_disp = "[FREE]"
    else:
        price_disp = f"[${cost_structure['cost_1mT_input_USD']:.2f}/mT]"
        
    print_name_part2 = f"{provider_short} {quantization} {flags_str} {price_disp}"
    
    # Full Name
    print_name_1 = f"{print_name_part1} - {print_name_part2} ({provider_name})"

    # --- 7. Result ---
    return {
        "id": unique_id,
        "developer_id": developer,
        "access_provider_id": "OpenRouter",
        "access_provider_short": "OR",
        "hosting_provider_id": provider_name,
        "hosting_provider_short": provider_short,
        "base_model_id": base_id,
        "base_model_name": model_name,
        "print_name_1": print_name_1,
        "print_name_part1": print_name_part1,
        "print_name_part2": print_name_part2,
        "capabilities": capabilities,
        "cost": cost_structure,
        "technical": technical,
        "raw_base_model_data": base_json,  # Store full JSON
        "raw_endpoint_data": endpoint_json, # Store full JSON
        "created_at": None, # Set by DB
        "updated_at": None  # Set by DB
    }
