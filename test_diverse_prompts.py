import asyncio
import time
import json
import os
from datetime import datetime
from backend.council import run_full_council
from backend.storage import storage

async def run_test_scenario(name, query, chairman_feedback=None):
    print(f"\n{'='*20} STARTING TEST: {name} {'='*20}")
    conversation_id = f"test_{name.lower().replace(' ', '_')}_{int(time.time())}"
    storage.create_conversation(conversation_id)
    
    logs = []
    def log_callback(msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {msg}")
        logs.append(f"[{timestamp}] {msg}")

    try:
        # Initial run
        result = await run_full_council(query, conversation_id=conversation_id, log_callback=log_callback)
        
        # Check if paused (Breakpoint) or if we want to simulate feedback
        session_state = storage.get_session_state(conversation_id)
        if session_state and (session_state.get("status") == "paused" or chairman_feedback):
            feedback = chairman_feedback or "Das Ergebnis ist okay, aber bitte vertiefe nochmals die kritischen Gegenargumente."
            print(f"\n[HUMAN CHAIR FEEDBACK]: {feedback}")
            result = await run_full_council(feedback, conversation_id=conversation_id, log_callback=log_callback)
            
        print(f"\n{'='*20} TEST COMPLETED: {name} {'='*20}")
        return True
    except Exception as e:
        print(f"❌ Error in test '{name}': {str(e)}")
        return False

async def main():
    scenarios = [
        {
            "name": "Political Debate",
            "query": "Sollte es eine allgemeine Dienstpflicht (sozial oder militärisch) in Deutschland geben? Erörtere Pro und Contra und finde einen tragfähigen Kompromiss.",
            "feedback": "Fokussiere dich stärker auf die logistischen Herausforderungen und die Kosten für den Staat."
        },
        {
            "name": "Coding Architecture",
            "query": "Entwirf eine skalierbare Architektur für eine Echtzeit-Kollaborations-App wie Notion. Berücksichtige Datenkonsistenz (CRDTs vs OT), Backend-Infrastruktur und Offline-Support.",
            "feedback": "Gehe tiefer auf die Vor- und Nachteile von CRDTs im Vergleich zu Operational Transformation (OT) ein."
        },
        {
            "name": "Creative Worldbuilding",
            "query": "Erschaffe eine originelle Science-Fiction-Welt, in der Wasser als Währung dient. Beschreibe die Gesellschaft, das Rechtssystem und die Technologie.",
            "feedback": "Wie gehen sie mit dem Recycling von Körperflüssigkeiten um? Das muss zentraler Bestandteil des Rechtssystems sein."
        }
    ]
    
    for scenario in scenarios:
        success = await run_test_scenario(scenario["name"], scenario["query"], scenario["feedback"])
        if success:
            # Short pause between tests to avoid rate limits
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())
