import asyncio
import httpx
import json
import os
import sys

# Add project root to path to import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.config import OPENROUTER_API_KEY

async def check_limit():
    print("Fetching OpenRouter models with limit=1000...")
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    
    async with httpx.AsyncClient() as client:
        # Try with a limit parameter, though not documented, just in case
        response = await client.get("https://openrouter.ai/api/v1/models?limit=1000", headers=headers)
        if response.status_code != 200:
            print(f"Error: {response.status_code} - {response.text}")
            return
            
        data = response.json()
        print(f"Response headers: {response.headers}")
        print(f"Response keys: {data.keys()}")
        models = data.get("data", [])
        
        print(f"Found {len(models)} models with limit=1000.")

        # Try without any params again to double check consistency
        response2 = await client.get("https://openrouter.ai/api/v1/models", headers=headers)
        data2 = response2.json()
        models2 = data2.get("data", [])
        print(f"Found {len(models2)} models without params.")

if __name__ == "__main__":
    asyncio.run(check_limit())
