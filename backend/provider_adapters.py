"""Provider adapter system for unified model access."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import re
from dataclasses import dataclass


@dataclass
class UnifiedModel:
    """Unified model representation."""
    developer_id: str
    access_provider_id: str
    access_provider_short: str
    hosting_provider_id: Optional[str]
    hosting_provider_short: Optional[str]
    base_model_id: str
    base_model_name: str
    variant_name: Optional[str]
    print_name_1: str
    print_name_part1: str
    print_name_part2: str
    capabilities: Dict[str, Any]
    cost: Dict[str, Any]
    technical: Dict[str, Any]
    latency_ms: Optional[float] = None
    last_latency_check: Optional[str] = None
    latency_live: Optional[float] = None
    latency_live_timestamp: Optional[str] = None
    provider_raw_data: Optional[Dict[str, Any]] = None


class BaseProviderAdapter(ABC):
    """Base interface for all provider adapters."""
    
    @abstractmethod
    async def fetch_models(self) -> List[Dict[str, Any]]:
        """Fetch raw model data from provider API."""
        pass
    
    @abstractmethod
    async def fetch_latencies(self, model_ids: List[str]) -> Dict[str, float]:
        """Fetch latency data for models."""
        pass
    
    @abstractmethod
    def normalize_model(self, raw_model: Dict[str, Any]) -> UnifiedModel:
        """Transform provider data to unified format."""
        pass
    
    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Get provider identifier."""
        pass
    
    @property
    @abstractmethod
    def provider_short(self) -> str:
        """Get short provider identifier."""
        pass


class OpenRouterAdapter(BaseProviderAdapter):
    """OpenRouter API adapter."""
    
    def __init__(self):
        from .config import OPENROUTER_API_KEY
        self.api_key = OPENROUTER_API_KEY
        self.base_url = "https://openrouter.ai/api/v1"
    
    @property
    def provider_id(self) -> str:
        return "OpenRouter"
    
    @property
    def provider_short(self) -> str:
        return "OR"
    
    async def fetch_models(self) -> List[Dict[str, Any]]:
        """Fetch all models from OpenRouter, including provider-specific endpoints."""
        import httpx
        import asyncio
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            # 1. Fetch base models
            response = await client.get(
                f"{self.base_url}/models",
                headers=headers
            )
            response.raise_for_status()
            base_models = response.json().get("data", [])
            
            # 2. Fetch endpoints for each model
            # Use a semaphore to limit concurrency and avoid rate limits
            semaphore = asyncio.Semaphore(10)
            
            async def fetch_endpoint(model):
                if isinstance(model, str):
                    print(f"WARNING: model is string: {model}")
                    return {}, []
                model_id = model.get("id")
                # Skip if model_id is missing
                if not model_id:
                    return model, []
                    
                url = f"{self.base_url}/models/{model_id}/endpoints"
                async with semaphore:
                    try:
                        resp = await client.get(url, headers=headers)
                        if resp.status_code == 200:
                            data = resp.json()
                            return model, data.get("data", [])
                    except Exception as e:
                        # Silently fail for individual endpoint fetch
                        # print(f"Error fetching endpoint for {model_id}: {e}")
                        pass
                return model, []
            
            tasks = [fetch_endpoint(m) for m in base_models]
            results = await asyncio.gather(*tasks)
            
            all_models = []
            for base_model, endpoints in results:
                if not isinstance(base_model, dict):
                    continue
                    
                # Add base model (Routed)
                all_models.append(base_model)
                
                # Add specific endpoints
                if isinstance(endpoints, dict):
                    print(f"DEBUG: endpoints is dict for {base_model.get('id')}: keys={list(endpoints.keys())}")
                    # Try to see if it's wrapped
                    if "data" in endpoints and isinstance(endpoints["data"], dict) and "endpoints" in endpoints["data"]:
                        endpoints = endpoints["data"]["endpoints"]
                    elif "endpoints" in endpoints:
                         endpoints = endpoints["endpoints"]
                    elif "data" in endpoints:
                         endpoints = endpoints["data"] # Fallback to previous logic if data is list
                    else:
                         # Treat as single endpoint? or just error?
                         endpoints = [endpoints]

                for ep in endpoints:
                    if isinstance(ep, str):
                        print(f"WARNING: endpoint is string: {ep}")
                        continue
                        
                    # Create a copy of base model and update with endpoint data
                    new_model = base_model.copy()
                    
                    provider_name = ep.get("provider_name", "Unknown")
                    # Sanitize provider name for ID suffix
                    safe_provider = provider_name.replace(" ", "_").replace("/", "_")
                    
                    # Construct new unique ID: original_id:ProviderName
                    new_model["id"] = f"{base_model['id']}:{safe_provider}"
                    
                    # Update name (e.g. "DeepInfra | openai/gpt-oss-120b")
                    new_model["name"] = ep.get("name", f"{provider_name} | {base_model['name']}")
                    
                    # Update pricing and technical details from endpoint
                    new_model["pricing"] = ep.get("pricing", base_model.get("pricing", {}))
                    new_model["context_length"] = ep.get("context_length", base_model.get("context_length", 0))
                    
                    # Store override for normalize
                    new_model["hosting_provider_override"] = provider_name
                    
                    # Store endpoint raw data for debugging/future use
                    new_model["endpoint_data"] = ep
                    
                    all_models.append(new_model)
                    
            return all_models
    
    async def fetch_latencies(self, model_ids: List[str]) -> Dict[str, float]:
        """Fetch latency data from OpenRouter models endpoint."""
        models = await self.fetch_models()
        latencies = {}
        
        for model in models:
            model_id = model.get('id')
            if model_id in model_ids:
                # OpenRouter provides latency in the model data
                # Latency is typically in milliseconds
                latency = self._extract_latency(model)
                if latency:
                    latencies[model_id] = latency
        
        return latencies
    
    def _extract_latency(self, model_data: Dict[str, Any]) -> Optional[float]:
        """Extract latency from OpenRouter model data."""
        # OpenRouter may provide latency in different fields
        # Check for latency information in the response
        latency_info = model_data.get('latency', {})
        
        if isinstance(latency_info, dict):
            return latency_info.get('average') or latency_info.get('p50') or latency_info.get('mean')
        elif isinstance(latency_info, (int, float)):
            return float(latency_info)
        
        # If no latency data available, return None
        return None
    
    def _determine_hosting_provider(self, raw_model: Dict[str, Any]) -> tuple[str, str]:
        """Determine hosting provider from raw model data."""
        # Check for override first (from provider-specific endpoints)
        if "hosting_provider_override" in raw_model:
            provider_id = raw_model["hosting_provider_override"]
            # Generate short code (first 2 chars uppercase)
            provider_short = provider_id[:2].upper() if len(provider_id) >= 2 else provider_id.upper()
            return provider_id, provider_short

        # Default
        provider_id = "OpenRouter"
        provider_short = "OR"
        
        # Check description and ID for known providers
        description = raw_model.get('description', '').lower()
        model_id = raw_model.get('id', '').lower()
        name = raw_model.get('name', '').lower()
        
        # Combine all text to search
        search_text = f"{description} {model_id} {name}"
        
        if "deepinfra" in search_text:
            provider_id = "DeepInfra"
            provider_short = "DI"
        elif "chute" in search_text:
            provider_id = "Chute"
            provider_short = "CH"
            
        return provider_id, provider_short

    def normalize_model(self, raw_model: Dict[str, Any]) -> UnifiedModel:
        """Transform OpenRouter model to unified format."""
        model_id = raw_model.get('id', '')
        name = raw_model.get('name', '')
        description = raw_model.get('description', '')
        context_length = raw_model.get('context_length', 0)
        
        # Parse developer and model name from OpenRouter ID
        # Format: provider/model-name[:variant]
        parts = model_id.split('/')
        if len(parts) >= 2:
            developer = parts[0]
            model_name_with_variant = '/'.join(parts[1:])
        else:
            developer = "Unknown"
            model_name_with_variant = model_id
        
        # Extract base model name and variant
        if ':' in model_name_with_variant:
            base_model_name, variant = model_name_with_variant.split(':', 1)
        else:
            base_model_name = model_name_with_variant
            variant = None
        
        # Clean up base model name
        base_model_name = self._clean_model_name(base_model_name)
        
        # Generate hierarchical ID
        base_model_id = self._generate_base_model_id(developer, base_model_name)
        
        # Extract pricing
        pricing = raw_model.get('pricing', {})
        prompt_price = self._extract_price(pricing.get('prompt', 0))
        completion_price = self._extract_price(pricing.get('completion', 0))
        
        # Determine cost structure
        is_free = prompt_price == 0 and completion_price == 0
        cost_structure = {
            "cost_1mT_input_USD": prompt_price * 1_000_000 if prompt_price > 0 else 0,
            "cost_1mT_output_USD": completion_price * 1_000_000 if completion_price > 0 else 0,
            "cost_currency": "USD",
            "cost_unit": "per_million_tokens",
            "is_free": is_free
        }
        
        # Extract capabilities
        capabilities = self._extract_capabilities(description, name, model_id)
        
        # Extract technical details
        technical = {
            "context_tokens": context_length,
            "max_output_tokens": raw_model.get('top_provider', {}).get('max_completion_tokens', 4096),
            "quantization": self._extract_quantization(model_id, description),
            "provider_specific": {
                "openrouter_id": model_id,
                "openrouter_name": name
            }
        }
        
        # Generate display names
        print_name_part1 = f"{developer}:{base_model_name}"
        
        # Create part2 with provider and cost info
        cost_display = "[FREE]" if is_free else f"[${cost_structure['cost_1mT_input_USD']:.2f}/mT]"
        
        # Get latency if available
        latency_info = raw_model.get('latency', {})
        latency_ms = None
        if isinstance(latency_info, dict):
            latency_ms = latency_info.get('average') or latency_info.get('p50')
        elif isinstance(latency_info, (int, float)):
            latency_ms = float(latency_info)
        
        latency_display = f" {latency_ms:.0f}ms" if latency_ms else ""
        
        # Format flags
        flags_str = self._capability_flags(capabilities)
        
        # Format quantization
        quantization = technical['quantization']
        
        # Create print_name_part2 (AccessProvider Quantization Flags Price)
        # Example: OR int4 R1 C1 V1 P1 $0.05/mT
        print_name_part2 = f"{self.provider_short} {quantization} {flags_str} {cost_display}"
        
        # Create print_name_1 (combine part1 with details)
        # Example: OpenAI:gpt-4o - OR int4 $2.50
        print_name_1 = f"{print_name_part1} - {self.provider_short} {quantization} {cost_display}"
        if variant:
             print_name_1 += f" ({variant})"

        # Determine hosting provider
        hosting_provider_id, hosting_provider_short = self._determine_hosting_provider(raw_model)
        
        return UnifiedModel(
            developer_id=developer,
            access_provider_id=self.provider_id,
            access_provider_short=self.provider_short,
            hosting_provider_id=hosting_provider_id, 
            hosting_provider_short=hosting_provider_short,
            base_model_id=base_model_id,
            base_model_name=base_model_name,
            variant_name=variant,
            print_name_1=print_name_1,
            print_name_part1=print_name_part1,
            print_name_part2=print_name_part2,
            capabilities=capabilities,
            cost=cost_structure,
            technical=technical,
            latency_ms=latency_ms,
            last_latency_check=datetime.utcnow().isoformat() if latency_ms else None,
            latency_live=None,
            latency_live_timestamp=None,
            provider_raw_data=raw_model
        )
    
    def _clean_model_name(self, name: str) -> str:
        """Clean and normalize model name."""
        # Remove common suffixes and prefixes
        name = re.sub(r'\s*(?:model|llm|ai)\s*', '', name, flags=re.IGNORECASE)
        name = re.sub(r'\s+', ' ', name).strip()
        return name
    
    def _generate_base_model_id(self, developer: str, model_name: str) -> str:
        """Generate base model ID in D.A.H.BN### format."""
        # For now, generate a simple hash-based ID
        # In production, this would be more sophisticated
        import hashlib
        combined = f"{developer}_{model_name}".lower()
        hash_obj = hashlib.md5(combined.encode())
        hash_hex = hash_obj.hexdigest()[:6]
        return f"BN{hash_hex}"
    
    def _extract_price(self, price_str) -> float:
        """Extract numeric price from OpenRouter pricing."""
        if price_str is None:
            return 0.0
        try:
            return float(price_str)
        except (ValueError, TypeError):
            return 0.0
    
    def _extract_capabilities(self, description: str, name: str, model_id: str) -> Dict[str, bool]:
        """Extract capabilities from model description and metadata."""
        text = f"{description} {name} {model_id}".lower()
        
        return {
            "toolUse": "tool" in text or "function calling" in text,
            "reasoning": any(keyword in text for keyword in ["reasoning", "think", "r1", "chain"]),
            "vision": any(keyword in text for keyword in ["vision", "visual", "multimodal", "vl", "image"]),
            "privacy": "privacy" in text or "local" in text,
            "caching": "cache" in text,
            "streamCancelling": "stream" in text,
            "long_context": "128k" in text or "200k" in text or "1m" in text,
            "coding": any(keyword in text for keyword in ["code", "coding", "programming"]),
            "creative": any(keyword in text for keyword in ["creative", "art", "write"]),
            "analysis": any(keyword in text for keyword in ["analysis", "analyze", "research"])
        }
    
    def _extract_quantization(self, model_id: str, description: str) -> str:
        """Extract quantization info from model ID or description."""
        text = f"{model_id} {description}".lower()
        
        if "fp8" in text:
            return "fp8"
        elif "fp16" in text:
            return "fp16"
        elif "int8" in text:
            return "int8"
        elif "int4" in text:
            return "int4"
        else:
            return "unknown"
    
    def _capability_flags(self, capabilities: Dict[str, bool]) -> str:
        """Generate capability flags string (R/C/V/P)."""
        flags = []
        
        # Reasoning
        if capabilities.get("reasoning"):
            flags.append("R1")
        else:
            flags.append("R0")
        
        # Coding
        if capabilities.get("coding"):
            flags.append("C1")
        else:
            flags.append("C0")
            
        # Vision
        if capabilities.get("vision"):
            flags.append("V1")
        else:
            flags.append("V0")
        
        # Privacy
        if capabilities.get("privacy"):
            flags.append("P1")
        else:
            flags.append("P0")
        
        return " ".join(flags)


class ProviderRegistry:
    """Registry for all provider adapters."""
    
    def __init__(self):
        self.adapters = {
            'openrouter': OpenRouterAdapter(),
            # Future adapters can be added here
            # 'openai': OpenAIAdapter(),
            # 'anthropic': AnthropicAdapter(),
        }
    
    def get_adapter(self, provider_id: str) -> Optional[BaseProviderAdapter]:
        """Get adapter by provider ID."""
        return self.adapters.get(provider_id.lower())
    
    def get_all_adapters(self) -> List[BaseProviderAdapter]:
        """Get all available adapters."""
        return list(self.adapters.values())
    
    async def fetch_all_models(self) -> List[UnifiedModel]:
        """Fetch and normalize models from all providers."""
        all_models = []
        
        for adapter in self.adapters.values():
            try:
                raw_models = await adapter.fetch_models()
                for raw_model in raw_models:
                    unified_model = adapter.normalize_model(raw_model)
                    all_models.append(unified_model)
            except Exception as e:
                print(f"Error fetching models from {adapter.provider_id}: {e}")
                continue
        
        return all_models
    
    async def update_latencies(self, models: List[UnifiedModel]) -> None:
        """Update latency data for all models."""
        # Group models by provider
        by_provider = {}
        for model in models:
            provider_id = model.access_provider_id.lower()
            if provider_id not in by_provider:
                by_provider[provider_id] = []
            by_provider[provider_id].append(model)
        
        # Update latencies per provider
        for provider_id, provider_models in by_provider.items():
            adapter = self.adapters.get(provider_id)
            if not adapter:
                continue
            
            model_ids = [m.provider_raw_data.get('id') for m in provider_models if m.provider_raw_data]
            if not model_ids:
                continue
            
            try:
                latencies = await adapter.fetch_latencies(model_ids)
                
                # Update models with latency data
                for model in provider_models:
                    raw_id = model.provider_raw_data.get('id')
                    if raw_id in latencies:
                        model.latency_ms = latencies[raw_id]
                        model.last_latency_check = datetime.utcnow().isoformat()
            except Exception as e:
                print(f"Error updating latencies for {adapter.provider_id}: {e}")
                continue


# Global registry instance
provider_registry = ProviderRegistry()
