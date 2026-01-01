import asyncio
import sys
import os
import json
import time
from datetime import datetime

# Add the project root to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend import council
from backend.storage import storage

async def run_detailed_test():
    conversation_id = f"test_stock_analysis_{int(time.time())}"
    storage.create_conversation(conversation_id)
    
    logs = []
    def log_callback(msg):
        timestamp = datetime.now().isoformat()
        log_entry = f"[{timestamp}] {msg}"
        logs.append(log_entry)
        print(log_entry)

    user_query = "Analyze the performance of VinFast (VFS) stock. Focus on short-term outlook, production targets, and recent financial volatility. Provide a concise report."
    
    # Save the "Stock Report 01 -short" prompt to DB for the test
    prompt_data = {
        "id": "stock_report_01_short",
        "title": "Stock Report 01 -short",
        "content": "Analyze the performance of [stock] stock. Focus on short-term outlook, production targets, and recent financial volatility. Provide a concise report.",
        "tags": ["finance", "stock", "analysis"]
    }
    storage.save_prompt(prompt_data)
    
    log_callback(f"Starting Stock Report 01 for VinFast (VFS) with 60s timeout...")
    
    try:
        # Step 1: Run the council (Stage 0 to 3)
        # Note: run_full_council might hit a breakpoint if configured
        result = await council.run_full_council(user_query, conversation_id=conversation_id, log_callback=log_callback)
        
        # Check for breakpoint/paused status
        session_state = storage.get_session_state(conversation_id)
        if session_state and session_state.get("status") == "paused":
            print("\n--- BREAKPOINT REACHED ---")
            # As Human Chair, I approve and provide a specific instruction
            human_feedback = "I want more focus on the impact of AI integration in their hardware lineup (iPhone/Mac). Please proceed."
            print(f"Human Chair Feedback: {human_feedback}")
            result = await council.run_full_council(human_feedback, conversation_id=conversation_id, log_callback=log_callback)

        # Final evaluation
        print("\n=== FINAL COUNCIL RESPONSE ===\n")
        print(json.dumps(result, indent=2))
        
        # Save logs and result for analysis
        test_data = {
            "conversation_id": conversation_id,
            "query": user_query,
            "logs": logs,
            "final_result": result,
            "audit_logs": storage.get_audit_logs(conversation_id)
        }
        
        with open("test_results_stock.json", "w") as f:
            json.dump(test_data, f, indent=2)
            
        print(f"\nTest data saved to test_results_stock.json")
        
    except Exception as e:
        print(f"\nERROR during test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_detailed_test())
