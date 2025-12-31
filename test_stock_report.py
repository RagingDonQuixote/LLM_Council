import asyncio
import sys
import os

# Add the project root to sys.path so we can import backend
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend import council
from backend.models_service import models_service
from backend import config

async def test_stock_report():
    print("Starting test with query: Apple Inc. AAPL\n")
    
    user_query = "Apple Inc. AAPL"
    
    # Mock log callback
    def log_callback(msg):
        print(f"[LOG] {msg}")

    try:
        # 1. Stage 0 test
        print("--- STAGE 0: ANALYZE AND PLAN ---")
        plan = await council.stage0_analyze_and_plan(user_query, log_callback=log_callback)
        print(f"Plan created: {plan.get('mission_name')}")
        
        # 2. Run the council
        print("\n--- RUNNING FULL COUNCIL ---")
        # We need a conversation ID for storage
        import time
        conv_id = f"test_conv_stock_report_{int(time.time())}"
        from backend.storage import storage
        storage.create_conversation(conv_id)
        
        results = await council.run_full_council(user_query, conversation_id=conv_id, log_callback=log_callback)        
        
        # Check if we hit a breakpoint
        session_state = storage.get_session_state(conv_id)
        if session_state and session_state.get("status") == "paused":
            print("\n--- BREAKPOINT REACHED ---")
            print("Simulating Human Chair approval...")
            # Simulate user approval
            results = await council.run_full_council("Approved. Please proceed with the financial analysis.", conversation_id=conv_id, log_callback=log_callback)

        print("\nCouncil execution finished.")
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_stock_report())
