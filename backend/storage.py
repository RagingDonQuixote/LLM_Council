"""SQLite-based storage for conversations, settings, and templates."""

import sqlite3
import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from .config import DB_PATH

class Storage:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or DB_PATH
        self.init_db()

    def get_db_connection(self):
        """Create a database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        """Initialize the database schema."""
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        # Conversations table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            title TEXT DEFAULT 'New Conversation',
            created_at TEXT NOT NULL,
            last_modified TEXT NOT NULL
        )
        ''')
        
        # Messages table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT,
            stage1 TEXT, -- JSON
            stage2 TEXT, -- JSON
            stage3 TEXT, -- JSON
            metadata TEXT, -- JSON
            created_at TEXT NOT NULL,
            FOREIGN KEY (conversation_id) REFERENCES conversations (id) ON DELETE CASCADE
        )
        ''')
        
        # Templates table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS templates (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            system_prompt TEXT,
            models TEXT, -- JSON list of model IDs
            strategy TEXT,
            created_at TEXT NOT NULL
        )
        ''')
        
        # Settings table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT -- JSON
        )
        ''')

        # AI Boards table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS ai_boards (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            config TEXT, -- JSON of full config
            usage_count INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            last_used TEXT
        )
        ''')

        # Prompts table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS prompts (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            tags TEXT, -- JSON list of strings
            rating INTEGER DEFAULT 0,
            usage_count INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        )
        ''')

        # Audit Logs table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            task_id TEXT,
            step TEXT, -- e.g., 'stage0_plan', 'stage1_query', 'chairman_decision'
            model_id TEXT,
            log_message TEXT,
            raw_data TEXT, -- JSON (raw response, ranking, etc.)
            metadata TEXT, -- JSON
            FOREIGN KEY (conversation_id) REFERENCES conversations (id) ON DELETE CASCADE
        )
        ''')
        
        # Add missing columns if they don't exist (for existing DBs)
        try:
            cursor.execute("ALTER TABLE prompts ADD COLUMN rating INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass # Column already exists
            
        try:
            cursor.execute("ALTER TABLE prompts ADD COLUMN usage_count INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass # Column already exists
            
        try:
            cursor.execute("ALTER TABLE conversations ADD COLUMN session_state TEXT")
        except sqlite3.OperationalError:
            pass # Column already exists

        try:
            cursor.execute("ALTER TABLE conversations ADD COLUMN archived INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass # Column already exists

        # Fail Lists table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS fail_lists (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            failed_models TEXT, -- JSON list
            created_at TEXT NOT NULL,
            is_active INTEGER DEFAULT 0
        )
        ''')
        
        # Unified Models table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS unified_models (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            developer_id TEXT NOT NULL,
            access_provider_id TEXT NOT NULL,
            access_provider_short TEXT NOT NULL,
            hosting_provider_id TEXT,
            hosting_provider_short TEXT,
            base_model_id TEXT NOT NULL,
            base_model_name TEXT NOT NULL,
            variant_name TEXT,
            print_name_1 TEXT NOT NULL,
            print_name_part1 TEXT NOT NULL,
            print_name_part2 TEXT NOT NULL,
            capabilities TEXT NOT NULL, -- JSON
            cost TEXT NOT NULL, -- JSON
            technical TEXT NOT NULL, -- JSON
            latency_ms REAL,
            last_latency_check TEXT,
            provider_raw_data TEXT, -- JSON
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            latency_live REAL,
            latency_live_timestamp TEXT,
            UNIQUE(developer_id, access_provider_id, hosting_provider_id, base_model_id, variant_name)
        )
        ''')
        
        # Add missing columns for unified_models if they don't exist
        try:
            cursor.execute("ALTER TABLE unified_models ADD COLUMN latency_live REAL")
        except sqlite3.OperationalError:
            pass
            
        try:
            cursor.execute("ALTER TABLE unified_models ADD COLUMN latency_live_timestamp TEXT")
        except sqlite3.OperationalError:
            pass
        
        # Indexes for performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_unified_models_search ON unified_models(print_name_1, base_model_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_unified_models_capabilities ON unified_models(capabilities)")
        
        # API Keys table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS api_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            provider TEXT NOT NULL, -- openrouter, openai, anthropic, etc.
            key_hash TEXT NOT NULL, -- we store the full key for now but could hash it. User asked for local storage.
            key_value TEXT NOT NULL,
            label TEXT, -- Generated short name e.g. "sk-or...8912z"
            description TEXT, -- User notes
            limit_amount REAL, -- e.g. 5.0
            limit_reset TEXT, -- daily, weekly, monthly
            usage_amount REAL,
            limit_remaining REAL,
            is_active INTEGER DEFAULT 1,
            created_at TEXT NOT NULL,
            last_checked TEXT -- When we last checked with provider API
        )
        ''')

        conn.commit()
        conn.close()
        
        # ToBeDeleted_start
        # # Add default templates if empty
        # if not self.list_templates():
        #     default_templates = [
        #         {
        #             "id": "creative",
        #             "name": "Kreative Aufgabe",
        #             "description": "Fokus auf Brainstorming und unkonventionelle Ideen.",
        #             "system_prompt": "Sei kreativ, originell und denke out-of-the-box.",
        #             "models": [], # use default
        #             "strategy": "borda"
        #         },
        #         {
        #             "id": "analysis",
        #             "name": "Aktienanalyse / Logik",
        #             "description": "Präzise, datengesteuerte Analyse mit Fokus auf Konsens.",
        #             "system_prompt": "Analysiere die Faktenlage präzise. Sei kritisch gegenüber Annahmen.",
        #             "models": [], # use default
        #             "strategy": "chairman"
        #         },
        #         {
        #             "id": "political",
        #             "name": "Politische Diskussion",
        #             "description": "Abwägung verschiedener Perspektiven und Argumente.",
        #             "system_prompt": "Berücksichtige verschiedene politische und gesellschaftliche Standpunkte neutral.",
        #             "models": [], # use default
        #             "strategy": "borda"
        #         }
        #     ]
        #     for t in default_templates:
        #         self.save_template(t)
        # ToBeDeleted_end
        pass

    def create_conversation(self, conversation_id: Optional[str] = None) -> Dict[str, Any]:
        """Create a new conversation."""
        import uuid
        if not conversation_id:
            conversation_id = str(uuid.uuid4())
            
        now = datetime.utcnow().isoformat()
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO conversations (id, created_at, last_modified) VALUES (?, ?, ?)",
            (conversation_id, now, now)
        )
        conn.commit()
        conn.close()
        
        return {
            "id": conversation_id,
            "created_at": now,
            "title": "New Conversation",
            "messages": []
        }

    def get_session_state(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get the session state for a conversation."""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT session_state FROM conversations WHERE id = ?", (conversation_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row and row[0]:
            import json
            return json.loads(row[0])
        return None

    def update_session_state(self, conversation_id: str, state: Dict[str, Any]):
        """Update the session state for a conversation."""
        import json
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE conversations SET session_state = ?, last_modified = CURRENT_TIMESTAMP WHERE id = ?",
            (json.dumps(state), conversation_id)
        )
        conn.commit()
        conn.close()

    def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Load a conversation and its messages."""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        # Get conversation metadata
        cursor.execute("SELECT * FROM conversations WHERE id = ?", (conversation_id,))
        conv_row = cursor.fetchone()
        if not conv_row:
            conn.close()
            return None
        
        # Get messages
        cursor.execute("SELECT * FROM messages WHERE conversation_id = ? ORDER BY id ASC", (conversation_id,))
        message_rows = cursor.fetchall()
        
        messages = []
        for row in message_rows:
            msg = {
                "role": row["role"],
                "content": row["content"]
            }
            if row["stage1"]: msg["stage1"] = json.loads(row["stage1"])
            if row["stage2"]: msg["stage2"] = json.loads(row["stage2"])
            if row["stage3"]: msg["stage3"] = json.loads(row["stage3"])
            if row["metadata"]: msg["metadata"] = json.loads(row["metadata"])
            messages.append(msg)
        
        conn.close()
        
        return {
            "id": conv_row["id"],
            "title": conv_row["title"],
            "created_at": conv_row["created_at"],
            "last_modified": conv_row["last_modified"],
            "session_state": json.loads(conv_row["session_state"]) if conv_row["session_state"] else None,
            "messages": messages
        }

    def archive_conversation(self, conversation_id: str) -> bool:
        """Archive a conversation."""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE conversations SET archived = 1 WHERE id = ?", (conversation_id,))
        updated = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return updated

    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation permanently (includes logs via CASCADE)."""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return deleted

    def reset_conversation(self, conversation_id: str) -> bool:
        """Reset a conversation (delete messages and session state)."""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
        cursor.execute("DELETE FROM audit_logs WHERE conversation_id = ?", (conversation_id,))
        cursor.execute("UPDATE conversations SET session_state = NULL, last_modified = CURRENT_TIMESTAMP WHERE id = ?", (conversation_id,))
        conn.commit()
        conn.close()
        return True

    def list_conversations(self, include_archived: bool = False) -> List[Dict[str, Any]]:
        """List all conversations (metadata only)."""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        where_clause = "" if include_archived else "WHERE archived = 0"
        
        cursor.execute(f'''
            SELECT c.*, 
                   (SELECT COUNT(*) FROM messages WHERE conversation_id = c.id) as message_count,
                   (SELECT COUNT(*) FROM messages WHERE conversation_id = c.id AND role = 'assistant') as revision_count
            FROM conversations c
            {where_clause}
            ORDER BY last_modified DESC
        ''')
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]

    def save_fail_list(self, name: str, failed_models: List[str]) -> int:
        """Save a fail list, keeping only the last 5."""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat()
        
        # Insert new list
        cursor.execute(
            "INSERT INTO fail_lists (name, failed_models, created_at) VALUES (?, ?, ?)",
            (name, json.dumps(failed_models), now)
        )
        new_id = cursor.lastrowid
        
        # Keep only the last 5
        cursor.execute("SELECT id FROM fail_lists ORDER BY created_at DESC")
        all_ids = [row[0] for row in cursor.fetchall()]
        if len(all_ids) > 5:
            ids_to_delete = all_ids[5:]
            cursor.execute(f"DELETE FROM fail_lists WHERE id IN ({','.join(['?']*len(ids_to_delete))})", ids_to_delete)
        
        conn.commit()
        conn.close()
        return new_id

    def get_fail_lists(self) -> List[Dict[str, Any]]:
        """Get all fail lists."""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM fail_lists ORDER BY created_at DESC")
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def set_active_fail_list(self, fail_list_id: int):
        """Set a fail list as active."""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE fail_lists SET is_active = 0")
        cursor.execute("UPDATE fail_lists SET is_active = 1 WHERE id = ?", (fail_list_id,))
        conn.commit()
        conn.close()

    def get_active_fail_list(self) -> Optional[List[str]]:
        """Get the currently active fail list's models."""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT failed_models FROM fail_lists WHERE is_active = 1")
        row = cursor.fetchone()
        conn.close()
        if row and row[0]:
            return json.loads(row[0])
        return None

    def add_message(self, conversation_id: str, role: str, content: str = None, 
                    stage1: List = None, stage2: List = None, stage3: Dict = None, 
                    metadata: Dict = None):
        """Generic method to add any message."""
        now = datetime.utcnow().isoformat()
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            """INSERT INTO messages 
               (conversation_id, role, content, stage1, stage2, stage3, metadata, created_at) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                conversation_id, 
                role, 
                content,
                json.dumps(stage1) if stage1 else None, 
                json.dumps(stage2) if stage2 else None, 
                json.dumps(stage3) if stage3 else None, 
                json.dumps(metadata) if metadata else None,
                now
            )
        )
        
        cursor.execute(
            "UPDATE conversations SET last_modified = ? WHERE id = ?",
            (now, conversation_id)
        )
        
        conn.commit()
        conn.close()

    def add_user_message(self, conversation_id: str, content: str, role: str = "user"):
        """Add a user message."""
        self.add_message(conversation_id, role, content)

    def add_assistant_message(self, conversation_id: str, stage1: List, stage2: List, stage3: Dict, metadata: Dict):
        """Add an assistant message with all stages."""
        self.add_message(
            conversation_id, 
            "assistant", 
            content=stage3.get("response", ""),
            stage1=stage1, 
            stage2=stage2, 
            stage3=stage3, 
            metadata=metadata
        )

    def add_human_feedback(self, conversation_id: str, feedback: str, continue_discussion: bool):
        """Add human chairman feedback."""
        self.add_message(
            conversation_id,
            "human_feedback",
            content=feedback,
            metadata={"continue_discussion": continue_discussion}
        )

    def end_session_with_rating(self, conversation_id: str, rating: int):
        """End session and store rating."""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        # We can store this in metadata of the last message or in a new table.
        # For now, let's just add a message about it.
        self.add_message(
            conversation_id,
            "system",
            content=f"Session ended with rating: {rating}/5",
            metadata={"rating": rating}
        )
        conn.close()

    def add_audit_log(self, conversation_id: str, step: str, task_id: str = None, 
                      model_id: str = None, log_message: str = None, 
                      raw_data: Any = None, metadata: Dict = None):
        """Add a granular audit log entry."""
        now = datetime.utcnow().isoformat()
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            """INSERT INTO audit_logs 
               (conversation_id, timestamp, task_id, step, model_id, log_message, raw_data, metadata) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                conversation_id,
                now,
                task_id,
                step,
                model_id,
                log_message,
                json.dumps(raw_data) if raw_data is not None else None,
                json.dumps(metadata) if metadata else None
            )
        )
        conn.commit()
        conn.close()

    def get_audit_logs(self, conversation_id: str) -> List[Dict[str, Any]]:
        """Get all audit logs for a conversation."""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM audit_logs WHERE conversation_id = ? ORDER BY timestamp ASC",
            (conversation_id,)
        )
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def add_analysis_result(self, conversation_id: str, analysis: str):
        """Add an analysis result to the conversation's metadata."""
        session_state = self.get_session_state(conversation_id) or {}
        session_state["analysis_result"] = analysis
        self.update_session_state(conversation_id, session_state)

    def update_conversation_title(self, conversation_id: str, title: str):
        """Update conversation title."""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE conversations SET title = ? WHERE id = ?",
            (title, conversation_id)
        )
        conn.commit()
        conn.close()

    # API Key Management
    def get_key_for_model(self, model_id: str) -> Optional[str]:
        """
        Get the appropriate API key for a given model.
        Logic:
        1. Check if model is free (via unified_models or heuristic).
        2. If free, try to find a key labeled 'Free' or 'Budget: $0'.
        3. Else, use a paid key (default or specific).
        4. Fallback to any available OpenRouter key.
        """
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        # 1. Check if model is free
        # First check unified_models table
        is_free = False
        # Try to find by id (which might be variant id or base model id)
        # Note: model_id in council is usually the full ID (e.g. google/gemini-2.0-flash-exp:free)
        # We need to match this against unified_models. But unified_models stores broken down parts.
        # We can try to match provider_raw_data id if we stored it, or use heuristic.
        
        # Heuristic is faster and reliable for :free suffix
        if ":free" in model_id or "free" in model_id.lower():
            is_free = True
        
        if not is_free:
            # Check DB cost
            # We assume model_id might match access_provider_id or similar in unified_models
            # Or we just check if any model with this ID exists and is free
            # Since unified_models schema is complex, let's stick to heuristic + simple check if we can
            pass

        # 2. Get all OpenRouter keys
        cursor.execute("SELECT * FROM api_keys WHERE provider = 'openrouter' AND is_active = 1")
        keys = [dict(r) for r in cursor.fetchall()]
        conn.close()
        
        if not keys:
            return None
            
        # 3. Select key
        if is_free:
            # Look for "free" key
            for k in keys:
                label = (k.get("label") or "").lower()
                desc = (k.get("description") or "").lower()
                if "free" in label or "free" in desc or "$0" in label or "$0" in desc:
                    return k["key_value"]
            # Fallback to any key
            return keys[0]["key_value"]
        else:
            # Look for paid key (avoid keys explicitly marked as free only if possible)
            paid_keys = []
            for k in keys:
                label = (k.get("label") or "").lower()
                desc = (k.get("description") or "").lower()
                if "free" not in label and "free" not in desc and "$0" not in label:
                    paid_keys.append(k)
            
            if not paid_keys:
                paid_keys = keys
                
            # Prefer keys with remaining limit > 0
            for k in paid_keys:
                limit = k.get("limit_remaining")
                if limit is not None and limit > 0:
                    return k["key_value"]
            
            # Fallback: return the first paid/default key
            return paid_keys[0]["key_value"]

    def list_api_keys(self) -> List[Dict[str, Any]]:
        """List all API keys."""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM api_keys ORDER BY created_at DESC")
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def save_api_key(self, key_data: Dict[str, Any]) -> int:
        """Save or update an API key."""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat()
        
        if "id" in key_data and key_data["id"]:
            # Update
            cursor.execute(
                """UPDATE api_keys SET 
                   provider=?, key_value=?, label=?, description=?, 
                   limit_amount=?, limit_reset=?, usage_amount=?, 
                   limit_remaining=?, is_active=?, last_checked=?
                   WHERE id=?""",
                (
                    key_data["provider"],
                    key_data["key_value"],
                    key_data["label"],
                    key_data.get("description", ""),
                    key_data.get("limit_amount"),
                    key_data.get("limit_reset"),
                    key_data.get("usage_amount"),
                    key_data.get("limit_remaining"),
                    key_data.get("is_active", 1),
                    key_data.get("last_checked", now),
                    key_data["id"]
                )
            )
            key_id = key_data["id"]
        else:
            # Insert
            cursor.execute(
                """INSERT INTO api_keys 
                   (provider, key_hash, key_value, label, description, 
                    limit_amount, limit_reset, usage_amount, limit_remaining, 
                    is_active, created_at, last_checked) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    key_data["provider"],
                    "hash_placeholder", # Not used for logic, but kept for schema compat
                    key_data["key_value"],
                    key_data["label"],
                    key_data.get("description", ""),
                    key_data.get("limit_amount"),
                    key_data.get("limit_reset"),
                    key_data.get("usage_amount"),
                    key_data.get("limit_remaining"),
                    key_data.get("is_active", 1),
                    now,
                    key_data.get("last_checked", now)
                )
            )
            key_id = cursor.lastrowid
            
        conn.commit()
        conn.close()
        return key_id

    def delete_api_key(self, key_id: int):
        """Delete an API key."""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM api_keys WHERE id = ?", (key_id,))
        conn.commit()
        conn.close()

    def get_api_key(self, key_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific API key."""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM api_keys WHERE id = ?", (key_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    # Template Management
    def list_templates(self) -> List[Dict[str, Any]]:
        """List all templates."""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM templates ORDER BY name ASC")
        rows = cursor.fetchall()
        conn.close()
        return [
            {**dict(row), "models": json.loads(row["models"]) if row["models"] else []}
            for row in rows
        ]

    def save_template(self, template: Dict[str, Any]):
        """Save or update a template."""
        now = datetime.utcnow().isoformat()
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """INSERT OR REPLACE INTO templates 
               (id, name, description, system_prompt, models, strategy, created_at) 
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                template["id"],
                template["name"],
                template.get("description"),
                template.get("system_prompt"),
                json.dumps(template.get("models", [])),
                template.get("strategy"),
                template.get("created_at", now)
            )
        )
        conn.commit()
        conn.close()

    # Settings Management
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a setting value."""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return json.loads(row["value"])
        return default

    def set_setting(self, key: str, value: Any):
        """Set a setting value."""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, json.dumps(value))
        )
        conn.commit()
        conn.close()

    # AI Board Management
    def list_boards(self) -> List[Dict[str, Any]]:
        """List all AI boards."""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM ai_boards ORDER BY last_used DESC, created_at DESC")
        rows = cursor.fetchall()
        conn.close()
        return [
            {**dict(row), "config": json.loads(row["config"]) if row["config"] else {}}
            for row in rows
        ]

    def save_board(self, board: Dict[str, Any]):
        """Save or update an AI board."""
        now = datetime.utcnow().isoformat()
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        # Check if it's an update to usage_count only
        if "usage_only" in board and board["usage_only"]:
            cursor.execute(
                "UPDATE ai_boards SET usage_count = usage_count + 1, last_used = ? WHERE id = ?",
                (now, board["id"])
            )
        else:
            cursor.execute(
                """INSERT OR REPLACE INTO ai_boards 
                   (id, name, description, config, usage_count, created_at, last_used) 
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    board["id"],
                    board["name"],
                    board.get("description"),
                    json.dumps(board.get("config", {})),
                    board.get("usage_count", 0),
                    board.get("created_at", now),
                    board.get("last_used", now)
                )
            )
        
        conn.commit()
        conn.close()

    def delete_board(self, board_id: str):
        """Delete an AI board."""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM ai_boards WHERE id = ?", (board_id,))
        conn.commit()
        conn.close()

    # Prompt Management
    def list_prompts(self) -> List[Dict[str, Any]]:
        """List all prompts."""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM prompts ORDER BY created_at DESC")
        rows = cursor.fetchall()
        conn.close()
        return [
            {**dict(row), "tags": json.loads(row["tags"]) if row["tags"] else []}
            for row in rows
        ]

    def save_prompt(self, prompt: Dict[str, Any]):
        """Save or update a prompt."""
        now = datetime.utcnow().isoformat()
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """INSERT OR REPLACE INTO prompts 
               (id, title, content, tags, rating, usage_count, created_at) 
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                prompt["id"],
                prompt["title"],
                prompt["content"],
                json.dumps(prompt.get("tags", [])),
                prompt.get("rating", 0),
                prompt.get("usage_count", 0),
                prompt.get("created_at", now)
            )
        )
        conn.commit()
        conn.close()

    def track_prompt_usage(self, prompt_id: str):
        """Increment usage count for a prompt."""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE prompts SET usage_count = usage_count + 1 WHERE id = ?",
            (prompt_id,)
        )
        conn.commit()
        conn.close()

    def delete_prompt(self, prompt_id: str):
        """Delete a prompt."""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM prompts WHERE id = ?", (prompt_id,))
        conn.commit()
        conn.close()

    def save_config(self, config: Dict[str, Any]):
        """Helper to save full config."""
        self.set_setting("config", config)

    def load_config(self) -> Dict[str, Any]:
        """Helper to load full config with defaults."""
        return self.get_setting("config", {})

    def export_to_markdown(self, conversation_id: str, final_answer: str, query: str):
        """Export the final result of a conversation to a markdown file."""
        import os
        from datetime import datetime
        
        # Ensure we use an absolute path relative to the project root
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        export_dir = os.path.join(project_root, "exports")
        
        try:
            os.makedirs(export_dir, exist_ok=True)
            
            # Create a safe filename
            safe_title = "".join([c if c.isalnum() else "_" for c in query[:30]]).strip()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_{safe_title}.md"
            filepath = os.path.join(export_dir, filename)
            
            md_content = f"""# LLM Council Result
**Query:** {query}
**Date:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Conversation ID:** {conversation_id}

---

{final_answer}

---
*Generated by LLM Council v1.30*
"""
            
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(md_content)
                
            return filepath
        except Exception as e:
            print(f"Error creating markdown export: {str(e)}")
            return None

# Global instance for easy access
storage = Storage()
