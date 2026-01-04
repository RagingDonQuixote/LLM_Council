import asyncio
import httpx
import json

async def probe_endpoints():
    base_url = "https://openrouter.ai/api/v1"
    
    endpoints_to_test = [
        "/endpoints",
        "/providers",
        "/models/openai/gpt-oss-120b/endpoints",
        "/models/openai/gpt-oss-120b/providers",
        "/models?supported_parameters=tools", # Just to check if params change anything
    ]
    
    async with httpx.AsyncClient() as client:
        # Test 1: Fetch models without Auth
        print("Fetching /models without Auth...")
        resp = await client.get(f"{base_url}/models")
        if resp.status_code == 200:
            data = resp.json().get('data', [])
            print(f"Count without auth: {len(data)}")
            # Check for Seedream
            has_seedream = any("seedream" in m.get("id", "").lower() or "seedream" in m.get("name", "").lower() for m in data)
            print(f"Has Seedream without auth: {has_seedream}")
        else:
            print(f"Failed to fetch models without auth: {resp.status_code}")

        # Inspect content of endpoints
        print("\n--- Content of /models/openai/gpt-oss-120b/endpoints ---")
        resp = await client.get(f"{base_url}/models/openai/gpt-oss-120b/endpoints")
        print(json.dumps(resp.json(), indent=2))

        # Inspect content of providers
        print("\n--- Content of /providers ---")
        resp = await client.get(f"{base_url}/providers")
        data = resp.json()
        # Print first 2 providers to see schema
        print(json.dumps(data['data'][:2], indent=2))

if __name__ == "__main__":
    asyncio.run(probe_endpoints())
