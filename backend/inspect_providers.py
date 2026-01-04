import asyncio
import httpx
import json
import os
import sys

# Add project root to path to import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.config import OPENROUTER_API_KEY

async def inspect_openrouter_data():
    print("Fetching OpenRouter models (Authenticated)...")
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.get("https://openrouter.ai/api/v1/models", headers=headers)
        if response.status_code != 200:
            print(f"Error: {response.status_code} - {response.text}")
            return
            
        data = response.json()
        models = data.get("data", [])
        
        print(f"Found {len(models)} models.")
        
        # Dump all models to a file for manual inspection
        with open("backend/all_models_dump.json", "w") as f:
            json.dump(models, f, indent=2)
            
        print(f"Dumped {len(models)} models to backend/all_models_dump.json")
        
        # Check specifically for "gpt-oss-120b:free"
        print("\n--- Details for openai/gpt-oss-120b:free ---")
        for m in models:
            if m.get("id") == "openai/gpt-oss-120b:free":
                print(json.dumps(m, indent=2))
            
        # Check specifically for "120b"
        targets_120 = [m for m in models if "120b" in m.get("id", "").lower()]
        print(f"Found {len(targets_120)} '120b' models.")
        for t in targets_120:
            print(f"ID: {t.get('id')}")

    
    print("\n--- Deep Search for 'DeepInfra' or 'Chute' ---")
    found_any = False
    
    def recursive_search(obj, path=""):
        nonlocal found_any
        if isinstance(obj, dict):
            for k, v in obj.items():
                recursive_search(v, path + f".{k}")
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                recursive_search(v, path + f"[{i}]")
        elif isinstance(obj, str):
            if "deepinfra" in obj.lower() or "chute" in obj.lower():
                print(f"Found match in {path}: {obj}")
                found_any = True
                
    recursive_search(models, "models")
    
    if not found_any:
        print("No matches found in the entire JSON structure.")

if __name__ == "__main__":
    asyncio.run(inspect_openrouter_data())
