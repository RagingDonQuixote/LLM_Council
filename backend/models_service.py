"""Service for fetching model metadata and checking availability."""

import httpx
import asyncio
from typing import List, Dict, Any, Optional
from .config import OPENROUTER_API_KEY

OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"

class ModelsService:
    def __init__(self):
        self.base_url = OPENROUTER_MODELS_URL
        self._cache = {}
        self._last_fetch = 0

    async def fetch_model_metadata(self) -> List[Dict[str, Any]]:
        """Fetch all available models and their metadata from OpenRouter."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(self.base_url)
                response.raise_for_status()
                data = response.json()
                models = data.get("data", [])
                
                # Add a 'free' flag and capabilities for easier filtering/display in frontend
                for m in models:
                    pricing = m.get("pricing", {})
                    # Some models are free, check for "0" or 0.0
                    m["free"] = (
                        pricing.get("prompt") == "0" or 
                        pricing.get("prompt") == 0 or 
                        ":free" in m.get("id", "").lower()
                    )
                    
                    # Add capabilities
                    desc = m.get("description", "").lower()
                    name = m.get("name", "").lower()
                    m["capabilities"] = {
                        "thinking": "reasoning" in desc or "think" in name or "r1" in m["id"].lower(),
                        "tools": "tool" in desc or "function calling" in desc,
                        "vision": "vision" in desc or "vl" in m["id"].lower() or "multimodal" in desc
                    }
                return models
            except Exception as e:
                print(f"Error fetching model metadata: {e}")
                return []

    async def check_model_availability(self, model_id: str) -> bool:
        """Check if a specific model is currently responsive."""
        all_models = await self.fetch_model_metadata()
        return any(m["id"] == model_id for m in all_models)

# Global instance
models_service = ModelsService()
