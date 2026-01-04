
import asyncio
import os
import sys

# Add parent directory to path to allow importing backend modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.provider_adapters import provider_registry
from backend.unified_model_service import UnifiedModelService

async def update_models():
    print("Fetching models from providers...")
    models = await provider_registry.fetch_all_models()
    print(f"Fetched {len(models)} models.")
    
    service = UnifiedModelService()
    count = 0
    
    print("Saving models to database...")
    for model in models:
        try:
            service.save_unified_model(model)
            count += 1
            if count % 50 == 0:
                print(f"Saved {count} models...")
        except Exception as e:
            print(f"Error saving model {model.base_model_id}: {e}")
            
    print(f"Successfully updated {count} models.")

if __name__ == "__main__":
    asyncio.run(update_models())
