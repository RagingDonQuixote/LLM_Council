import os
import json
import zipfile
from datetime import datetime
from .storage import storage

def export_audit_archive(conversation_id: str, output_dir: str = "audits") -> str:
    """
    Creates a ZIP archive for a conversation containing all logs and data.
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Get all relevant data
    logs = storage.get_audit_logs(conversation_id)
    session_state = storage.get_session_state(conversation_id)
    messages = storage.get_messages(conversation_id)
    
    # Filename format: audit_CONVID_TIMESTAMP.zip
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_name = f"audit_{conversation_id}_{timestamp_str}.zip"
    archive_path = os.path.join(output_dir, archive_name)
    
    with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # 1. Export Audit Logs as individual files
        for i, log in enumerate(logs):
            # Prefix with timestamp for chronological order
            ts = log['timestamp'].replace(':', '-').replace('.', '-')
            step = log['step']
            model = (log['model_id'] or "unknown").split('/')[-1]
            filename = f"logs/{ts}_{i:03d}_{step}_{model}.json"
            
            # Prepare log content
            log_content = {
                "timestamp": log['timestamp'],
                "step": log['step'],
                "task_id": log['task_id'],
                "model": log['model_id'],
                "message": log['log_message'],
                "raw_data": json.loads(log['raw_data']) if log['raw_data'] else None,
                "metadata": json.loads(log['metadata']) if log['metadata'] else None
            }
            zipf.writestr(filename, json.dumps(log_content, indent=2))
            
        # 2. Export full conversation history
        chat_history = []
        for msg in messages:
            chat_history.append({
                "role": msg['role'],
                "content": msg['content'],
                "timestamp": msg['created_at']
            })
        zipf.writestr("conversation_history.json", json.dumps(chat_history, indent=2))
        
        # 3. Export Session State (includes Analysis Result)
        zipf.writestr("session_state.json", json.dumps(session_state, indent=2))
        
        # 4. Export Analysis Result specifically if it exists
        if session_state and "analysis_result" in session_state:
            zipf.writestr("ANALYSIS_RESULT.txt", session_state["analysis_result"])
            
    return archive_path
