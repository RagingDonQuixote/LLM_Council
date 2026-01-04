import sqlite3
import json
import os
from datetime import datetime
from merger import merge_endpoint_strategy

DB_PATH = "D:/DB_LLM_Council/council.db"

def init_umt_table(cursor):
    """Initialize Unified Models Table with NEW schema including raw columns."""
    print("Re-creating unified_models table...")
    cursor.execute("DROP TABLE IF EXISTS unified_models")
    
    # Note: We are adding raw_base_model_data and raw_endpoint_data
    cursor.execute("""
        CREATE TABLE unified_models (
            id TEXT PRIMARY KEY,
            developer_id TEXT,
            access_provider_id TEXT,
            access_provider_short TEXT,
            hosting_provider_id TEXT,
            hosting_provider_short TEXT,
            base_model_id TEXT,
            base_model_name TEXT,
            variant_name TEXT,
            print_name_1 TEXT,
            print_name_part1 TEXT,
            print_name_part2 TEXT,
            capabilities TEXT,
            cost TEXT,
            technical TEXT,
            latency_ms REAL,
            last_latency_check TEXT,
            provider_raw_data TEXT,
            raw_base_model_data TEXT,
            raw_endpoint_data TEXT,
            created_at TEXT,
            updated_at TEXT,
            latency_live REAL,
            latency_live_timestamp TEXT
        )
    """)

def process_data():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 1. Init Table
    init_umt_table(cursor)
    
    # 2. Fetch Raw Base Models
    print("Fetching raw base models...")
    cursor.execute("SELECT * FROM raw_openrouter_models")
    base_models = {row['id']: json.loads(row['raw_json']) for row in cursor.fetchall()}
    print(f"Loaded {len(base_models)} base models.")
    
    # 3. Fetch Raw Endpoints
    print("Fetching raw endpoints...")
    cursor.execute("SELECT * FROM raw_openrouter_endpoints")
    endpoint_rows = cursor.fetchall()
    print(f"Loaded {len(endpoint_rows)} endpoint containers.")
    
    count_inserted = 0
    
    # 4. Process and Merge
    for row in endpoint_rows:
        model_id = row['model_id']
        endpoint_container = json.loads(row['raw_json'])
        
        # Get matching base model
        base_model_json = base_models.get(model_id)
        if not base_model_json:
            print(f"Warning: No base model found for {model_id}, skipping.")
            continue
            
        # Extract actual endpoints list from container
        endpoints_list = []
        
        # Logic to handle OpenRouter's nested structure
        # Structure 1: endpoint_container['response']['data'] is list
        # Structure 2: endpoint_container['response']['data'] is dict with 'endpoints' list
        
        resp_data = endpoint_container.get('response', {}).get('data')
        
        if isinstance(resp_data, list):
            endpoints_list = resp_data
        elif isinstance(resp_data, dict) and 'endpoints' in resp_data:
            endpoints_list = resp_data['endpoints']
        else:
            # Maybe single object or empty?
            if resp_data:
                endpoints_list = [resp_data] if isinstance(resp_data, dict) else []
                
        if not endpoints_list:
            # Create a "dummy" endpoint if none exists, just to show the base model?
            # User policy: "Die Daten im endpoint sind immer die entscheidenden"
            # If no endpoint, maybe the base model IS the endpoint (OpenRouter routed)?
            # Let's create a minimal endpoint representing "Auto/Routed"
            endpoints_list = [{
                "provider_name": "OpenRouter",
                "pricing": base_model_json.get("pricing"),
                "context_length": base_model_json.get("context_length")
            }]
            
        for ep in endpoints_list:
            if isinstance(ep, str): continue # Skip string garbage if any
            
            # MERGE LOGIC
            unified_data = merge_endpoint_strategy(base_model_json, ep)
            
            # INSERT
            now = datetime.utcnow().isoformat()
            
            # Handle potential duplicate IDs (if multiple endpoints have same provider name for same model)
            # We append a counter if needed? Or just overwrite?
            # For now, let's try insert and catch error
            
            try:
                cursor.execute("""
                    INSERT INTO unified_models (
                        id, developer_id, access_provider_id, access_provider_short,
                        hosting_provider_id, hosting_provider_short, base_model_id,
                        base_model_name, print_name_1, print_name_part1, print_name_part2,
                        capabilities, cost, technical, raw_base_model_data, raw_endpoint_data,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    unified_data['id'],
                    unified_data['developer_id'],
                    unified_data['access_provider_id'],
                    unified_data['access_provider_short'],
                    unified_data['hosting_provider_id'],
                    unified_data['hosting_provider_short'],
                    unified_data['base_model_id'],
                    unified_data['base_model_name'],
                    unified_data['print_name_1'],
                    unified_data['print_name_part1'],
                    unified_data['print_name_part2'],
                    json.dumps(unified_data['capabilities']),
                    json.dumps(unified_data['cost']),
                    json.dumps(unified_data['technical']),
                    json.dumps(unified_data['raw_base_model_data']),
                    json.dumps(unified_data['raw_endpoint_data']),
                    now, now
                ))
                count_inserted += 1
            except sqlite3.IntegrityError:
                print(f"Duplicate ID skipped: {unified_data['id']}")
            except Exception as e:
                print(f"Error inserting {unified_data['id']}: {e}")

    conn.commit()
    conn.close()
    print(f"Successfully processed and inserted {count_inserted} unified models.")

if __name__ == "__main__":
    process_data()
