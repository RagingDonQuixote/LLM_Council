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
        # ToBeDeleted_start
        # return self.get_setting("config", {
        #     "council_models": [],
        #     "chairman_model": "",
        #     "consensus_strategy": "borda",
        #     "response_timeout": 30,
        #     "model_personalities": {}
        # })
        # ToBeDeleted_end
        return self.get_setting("config", {})

# Global instance for easy access
storage = Storage()
