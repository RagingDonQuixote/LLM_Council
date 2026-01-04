import asyncio
import httpx
import json
import os

# Use your API key here
API_KEY = "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"
BASE_URL = "https://openrouter.ai/api/v1"

async def main():
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        print("1. Fetching base list from /models ...")
        response = await client.get(f"{BASE_URL}/models", headers=headers)
        if response.status_code != 200:
            print(f"Error: {response.status_code}")
            return
            
        all_models = response.json().get("data", [])
        # Let's pick 'openai/gpt-oss-120b' as requested by user context
        target_id = "openai/gpt-oss-120b"
        
        base_model_data = next((m for m in all_models if m["id"] == target_id), None)
        
        if not base_model_data:
            print(f"Could not find {target_id} in /models list.")
            # Fallback to another one if needed
            base_model_data = all_models[0]
            target_id = base_model_data["id"]
            print(f"Using {target_id} instead.")
            
        print(f"\n--- BASE MODEL DATA (/models) for {target_id} ---")
        print(json.dumps(base_model_data, indent=2))
        base_keys = set(base_model_data.keys())

        print(f"\n2. Fetching endpoints from /models/{target_id}/endpoints ...")
        url = f"{BASE_URL}/models/{target_id}/endpoints"
        resp = await client.get(url, headers=headers)
        
        if resp.status_code != 200:
            print(f"Error fetching endpoints: {resp.status_code}")
            return
            
        endpoints_response = resp.json()
        
        # Handle the structure we found earlier
        endpoints_list = []
        if "data" in endpoints_response:
            data_obj = endpoints_response["data"]
            if isinstance(data_obj, dict) and "endpoints" in data_obj:
                endpoints_list = data_obj["endpoints"]
            elif isinstance(data_obj, list):
                endpoints_list = data_obj
        
        print(f"\nFound {len(endpoints_list)} endpoints.")
        
        if not endpoints_list:
            print("No endpoints found to compare.")
            return

        first_endpoint = endpoints_list[0]
        print(f"\n--- FIRST ENDPOINT DATA (/endpoints) ---")
        print(json.dumps(first_endpoint, indent=2))
        
        endpoint_keys = set(first_endpoint.keys())
        
        print(f"\n--- COMPARISON ---")
        missing_in_endpoint = base_keys - endpoint_keys
        extra_in_endpoint = endpoint_keys - base_keys
        common_keys = base_keys.intersection(endpoint_keys)
        
        print(f"Keys in Base but MISSING in Endpoint: {missing_in_endpoint}")
        print(f"Keys EXTRA in Endpoint: {extra_in_endpoint}")
        print(f"Common Keys: {common_keys}")
        
        # Check specific values for common keys to see if they differ
        print("\n--- VALUE COMPARISON (Common Keys) ---")
        for key in common_keys:
            base_val = base_model_data.get(key)
            end_val = first_endpoint.get(key)
            if base_val != end_val:
                print(f"DIFFERENCE in '{key}':")
                print(f"  Base: {base_val}")
                print(f"  Endp: {end_val}")
            else:
                # print(f"  '{key}' matches.")
                pass

if __name__ == "__main__":
    asyncio.run(main())
