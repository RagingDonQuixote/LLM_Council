import asyncio
import httpx
import json
import os
import shutil
import sqlite3
from datetime import datetime

# Configuration
API_KEY = "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"
BASE_URL = "https://openrouter.ai/api/v1"
DB_PATH = "D:/DB_LLM_Council/council.db"
DATA_DIR = "F:/Nextcloud/PETER/10 CODING/140 LLM_Council/backend/data"

# Ensure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)

FILE_1_NAME = "OpenRouter_Abfrage1_raw.json"
FILE_2_NAME = "OpenRouter_Abfrage2_raw.json"

async def manage_files():
    """Rename existing raw files to _old"""
    for fname in [FILE_1_NAME, FILE_2_NAME]:
        fpath = os.path.join(DATA_DIR, fname)
        if os.path.exists(fpath):
            old_path = os.path.join(DATA_DIR, fname.replace(".json", "_old.json"))
            print(f"Renaming {fname} to {os.path.basename(old_path)}...")
            if os.path.exists(old_path):
                os.remove(old_path)
            os.rename(fpath, old_path)

async def fetch_all_raw_data():
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://llm-council.local", 
        "X-Title": "LLM Council"
    }
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        # --- 1. Fetch /models ---
        print("Fetching /models (Abfrage 1)...")
        resp1 = await client.get(f"{BASE_URL}/models", headers=headers)
        if resp1.status_code != 200:
            print(f"Error fetching models: {resp1.status_code}")
            return None, None
            
        data1 = resp1.json()
        models_list = data1.get("data", [])
        print(f"Fetched {len(models_list)} base models.")
        
        # Save File 1
        path1 = os.path.join(DATA_DIR, FILE_1_NAME)
        with open(path1, "w", encoding="utf-8") as f:
            json.dump(data1, f, indent=2)
            
        # --- 2. Fetch /endpoints for all models ---
        print("Fetching /endpoints for all models (Abfrage 2)...")
        
        semaphore = asyncio.Semaphore(15) # Limit concurrency
        results = []
        
        async def fetch_endpoint(model_id):
            url = f"{BASE_URL}/models/{model_id}/endpoints"
            async with semaphore:
                try:
                    resp = await client.get(url, headers=headers)
                    if resp.status_code == 200:
                        return {"model_id": model_id, "response": resp.json()}
                    else:
                        print(f"Failed to fetch endpoints for {model_id}: {resp.status_code}")
                        return {"model_id": model_id, "error": resp.status_code}
                except Exception as e:
                    print(f"Exception fetching endpoints for {model_id}: {e}")
                    return {"model_id": model_id, "error": str(e)}

        tasks = [fetch_endpoint(m["id"]) for m in models_list]
        
        # Show progress
        total = len(tasks)
        completed = 0
        
        # Use as_completed to show progress if needed, or just gather
        # gathering is simpler for code structure here
        endpoints_data = []
        for i in range(0, total, 50):
            batch = tasks[i:i+50]
            batch_results = await asyncio.gather(*batch)
            endpoints_data.extend(batch_results)
            print(f"Fetched endpoints: {min(i+50, total)}/{total}")
            
        # Save File 2
        path2 = os.path.join(DATA_DIR, FILE_2_NAME)
        wrapper = {
            "fetched_at": datetime.now().isoformat(),
            "count": len(endpoints_data),
            "data": endpoints_data
        }
        with open(path2, "w", encoding="utf-8") as f:
            json.dump(wrapper, f, indent=2)
            
        return models_list, endpoints_data

def update_db_tables(models, endpoints):
    """Create raw tables and insert data for viewing"""
    print(f"Updating DB at {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. raw_openrouter_models
    cursor.execute("DROP TABLE IF EXISTS raw_openrouter_models")
    cursor.execute("""
        CREATE TABLE raw_openrouter_models (
            id TEXT PRIMARY KEY,
            name TEXT,
            raw_json TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    print("Inserting into raw_openrouter_models...")
    for m in models:
        cursor.execute(
            "INSERT INTO raw_openrouter_models (id, name, raw_json) VALUES (?, ?, ?)",
            (m.get("id"), m.get("name"), json.dumps(m))
        )
        
    # 2. raw_openrouter_endpoints
    cursor.execute("DROP TABLE IF EXISTS raw_openrouter_endpoints")
    cursor.execute("""
        CREATE TABLE raw_openrouter_endpoints (
            model_id TEXT,
            endpoints_count INTEGER,
            raw_json TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    print("Inserting into raw_openrouter_endpoints...")
    for item in endpoints:
        model_id = item.get("model_id")
        resp = item.get("response", {})
        
        # Try to count endpoints
        count = 0
        if "data" in resp:
            data_obj = resp["data"]
            if isinstance(data_obj, list):
                count = len(data_obj)
            elif isinstance(data_obj, dict) and "endpoints" in data_obj:
                count = len(data_obj["endpoints"])
        
        cursor.execute(
            "INSERT INTO raw_openrouter_endpoints (model_id, endpoints_count, raw_json) VALUES (?, ?, ?)",
            (model_id, count, json.dumps(item))
        )
        
    conn.commit()
    conn.close()
    print("Database updated successfully.")

async def main():
    await manage_files()
    models, endpoints = await fetch_all_raw_data()
    if models and endpoints:
        update_db_tables(models, endpoints)

if __name__ == "__main__":
    asyncio.run(main())
