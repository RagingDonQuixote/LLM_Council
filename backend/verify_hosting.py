import sqlite3
import os

DB_PATH = "D:/DB_LLM_Council/council.db"

def verify_hosting():
    if not os.path.exists(DB_PATH):
        print(f"Error: Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("Checking for models with non-OpenRouter hosting...")
    cursor.execute('''
        SELECT id, base_model_name, hosting_provider_id, hosting_provider_short 
        FROM unified_models 
        WHERE hosting_provider_id != 'OpenRouter'
    ''')
    
    rows = cursor.fetchall()
    print(f"Found {len(rows)} models with custom hosting:")
    for row in rows:
        print(f"  {row[0]}: {row[2]} ({row[3]})")
        
    conn.close()

if __name__ == "__main__":
    verify_hosting()
